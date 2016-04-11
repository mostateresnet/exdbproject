from django.conf import settings
from collections import OrderedDict
from exdb.models import Email, Experience, ExperienceApproval
from itertools import groupby
from datetime import timedelta
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.contrib.contenttypes.models import ContentType
from django.utils.timezone import now, localtime
from django.core.mail import get_connection
from django.core.mail.message import EmailMessage, EmailMultiAlternatives
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _


def send_mass_mail(datatuple, fail_silently=False, user=None, password=None, connection=None):
    """
    Given a datatuple of (subject, text_content, html_content [optional], from_email,
    recipient_list), sends each message to each recipient list. Returns the
    number of emails sent.
    If from_email is None, the DEFAULT_FROM_EMAIL setting is used.
    If auth_user and auth_password are set, they're used to log in.
    If auth_user is None, the EMAIL_HOST_USER setting is used.
    If auth_password is None, the EMAIL_HOST_PASSWORD setting is used.
    """
    connection = connection or get_connection(
        username=user, password=password, fail_silently=fail_silently
    )

    messages = []
    for emailtuple in datatuple:
        if len(emailtuple) == 5:
            subject, text, html, from_email, recipient = emailtuple
            message = EmailMultiAlternatives(subject, text, from_email, recipient, connection=connection)
            message.attach_alternative(html, 'text/html')
        else:
            subject, text, from_email, recipient = emailtuple
            message = EmailMessage(subject, text, from_email, recipient, connection=connection)
        messages.append(message)

    return connection.send_messages(messages)

class EmailTaskBase(object):
    # task_name = "Email Task Base"

    def send(self, emails, *args, **kwargs):
        raise NotImplementedError('send must be overridden for EmailTaskBase')

    def get_addrs(self, *args, **kwargs):
        raise NotImplementedError('get_addrs must be overridden for EmailTaskBase')

    def sync_addrs(self, email_task):
        '''Creates Emails if they do not already exist
           Adds existing or created Emails to the EmailTask
           Removes Emails from the EmailTask if they are not in the list
        '''
        addrs = self.get_addrs()
        existing_addrs = Email.objects.filter(addr__in=addrs).values_list("addr", flat=True)

        addrs_to_create = set(addrs) - set(existing_addrs)
        new_emails = []
        for addr in addrs_to_create:
            new_emails.append(Email(addr=addr))
        Email.objects.bulk_create(new_emails)

        # if they aren't in the addrs list remove them
        email_task.emails.remove(*Email.objects.exclude(addr__in=addrs))

        # if they are in the list add them
        email_task.emails.add(*Email.objects.filter(addr__in=addrs))

        return len(addrs)


class DailyDigest(EmailTaskBase):
    """
    This email should be sent to any user who is an approver daily
    at 1600 local time.
    """
    task_name = "Daily Digest"

    def is_time_to_send(self):
        return True
        # Send the daily email at 1600
        right_now = localtime(now())
        return right_now.hour == 16 and(0 <= right_now.minute < 5)
    
    def get_addrs(self):
        """
        Return all the users who have a pending experience they need
        to approve, or an approval that needs evaluation
        """
        pending_experiences = Experience.objects.filter(status='pe')
        experience_approvals_needing_eval = ExperienceApproval.objects.filter(experience__status='ad', experience__end_datetime__lt=now())

        users = get_user_model().objects.filter(
            Q(approval_queue__pk__in=pending_experiences) |
            Q(approval_set__pk__in=experience_approvals_needing_eval)
        ).distinct()
        return users
    
    def send(self, email_task=False):
        if self.is_time_to_send():
            emails = []
            from_email = settings.SERVER_EMAIL
            subject = settings.EMAIL_SUBJECT_PREFIX + ' Daily Digest'
            for user in self.get_addrs():
                # Find all the approvals that need evaluation and all the experiences that need to be approved by the current user
                experience_approvals = ExperienceApproval.objects.filter(approver=user, experience__end_datetime__lt=now(), experience__status='ad')
                experiences = Experience.objects.filter(Q(next_approver=user, status='pe')|Q(pk__in=experience_approvals.values('experience')))
                experience_count = len(experiences)

                status_to_display = [_('Pending Approval'), _('Needs Evaluation')]
                experience_dict = OrderedDict()
                for status in status_to_display:
                    experience_dict[status] = []
                for experience in experiences:
                    if experience.needs_evaluation():
                        experience_dict[_('Needs Evaluation')].append(experience)
                    else:
                        experience_dict[_('Pending Approval')].append(experience)

                html = render_to_string('exdb/emails/test.html', {'experience_dict': experience_dict, 'experience_count': experience_count, 'url_prefix': settings.URL_PREFIX})
                text = strip_tags(html)
                recipients = (user.email,)
                emails.append((subject, text, html, from_email, recipients))
            send_mass_mail(emails)
            return len(emails)
        return 0


class ExperienceStatusUpdate(EmailTaskBase):
    """
    This email should be sent to any user who has an experience they
    authored that has changed in status to either approved or denied.
    """
    task_name = "Status Update"

    def get_addrs(self):
        return Experience.objects.filter(status__in=('de', 'ad'), last_status_change_datetime__isnull=False)

    def send(self, email_task=False):
        emails = []
        from_email = settings.SERVER_EMAIL
        subject = settings.EMAIL_SUBJECT_PREFIX + ' Experience status updated'
        for experience in self.get_addrs():
            user = experience.author

            html = render_to_string('exdb/emails/test.html', {'experience_dict': experience_dict, 'experience_count': experience_count, 'url_prefix': settings.URL_PREFIX})
            text = strip_tags(html)
            recipients = (user.email,)
            emails.append((subject, text, html, from_email, recipients))

            # Reset the datetime to null so we only send them one email
            experience.last_status_change_datetime = None
        send_mass_mail(emails)
        return len(emails)
