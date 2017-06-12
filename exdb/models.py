from importlib import import_module
from django.db import models
from django.utils.timezone import now
from django.conf import settings
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _
from django.core.validators import validate_email
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.auth.models import AbstractUser, UserManager
from django.forms.models import model_to_dict


class EXDBUser(AbstractUser):
    affiliation = models.ForeignKey('Affiliation', null=True)

    class EXDBUserQuerySet(models.QuerySet, UserManager):

        def hallstaff(self):
            return self.filter(groups__name__icontains='hallstaff')

    objects = EXDBUserQuerySet.as_manager()

    def approvable_experiences(self):
        if getattr(self, '_approvable_experiences', None) is None:
            self._approvable_experiences = self.approval_queue.filter(status='pe')
        return self._approvable_experiences

    def is_hallstaff(self):
        return self.__class__.objects.hallstaff().filter(pk=self.pk).exists()

    def __str__(self):
        return self.get_full_name() or self.email or self.username

    class Meta:
        ordering = ['first_name', 'last_name', 'email', 'username']


class Type(models.Model):
    name = models.CharField(max_length=300)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class Subtype(models.Model):
    name = models.CharField(max_length=300)
    needs_verification = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class Affiliation(models.Model):
    name = models.CharField(max_length=300)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class Section(models.Model):
    name = models.CharField(max_length=300)
    affiliation = models.ForeignKey(Affiliation)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class Keyword(models.Model):
    name = models.CharField(max_length=300)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class Experience(models.Model):
    # The last index of this tuple is the slug value for the status.
    # This is used mainly for the ListByStatus View.
    STATUS_TYPES = (
        ('de', _('Denied'), 'denied',),
        ('dr', _('Draft'), 'draft',),
        ('pe', _('Pending Approval'), 'pending-approval',),
        ('ad', _('Approved'), 'approved',),
        ('co', _('Completed'), 'completed',),
        ('ca', _('Cancelled'), 'cancelled',),
    )

    AUDIENCE_TYPES = (
        ('b', _('Building')),
        ('c', _('Campus')),
        ('f', _('Floor')),
    )

    FUND_TYPES = (
        ('na', _('Not necessary')),
        ('yn', _('Yes, but request not submitted yet')),
        ('ys', _('Yes, request submitted')),
        ('ya', _('Yes, request approved')),
    )

    author = models.ForeignKey(settings.AUTH_USER_MODEL)
    planners = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='planner_set', blank=True)
    recognition = models.ManyToManyField(Section, blank=True)
    name = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    type = models.ForeignKey(Type)
    subtypes = models.ManyToManyField(Subtype, blank=True, related_name='experience_set')
    goals = models.TextField(blank=True)
    keywords = models.ManyToManyField(Keyword, blank=True, related_name='keyword_set')
    audience = models.CharField(max_length=1, choices=AUDIENCE_TYPES, blank=True)
    guest = models.CharField(max_length=300, blank=True)
    guest_office = models.CharField(max_length=300, blank=True)
    attendance = models.IntegerField(null=True, blank=True)
    created_datetime = models.DateTimeField(default=now, blank=True)
    status = models.CharField(
        max_length=2,
        choices=tuple(
            statuses[:2] for statuses in STATUS_TYPES),
        default=STATUS_TYPES[1][0])
    next_approver = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True, related_name='approval_queue')
    funds = models.CharField(max_length=2, choices=FUND_TYPES, default='na')
    conclusion = models.TextField(
        blank=True,
        help_text=_('What went well? What would you change about this experience in the future?'),
    )

    # needs_author_email is to signify the author needs to recieve an email
    # after the status has changed to either approved or denied.
    needs_author_email = models.BooleanField(default=False)

    # last_evaluation_email_datetime is after an experience needs to be evaluated we
    # send an email, as well as every 24 hours after the email was sent until
    # the user evaluates it.
    last_evaluation_email_datetime = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name

    def needs_evaluation(self):
        return self.status == 'ad' and self.end_datetime <= now()

    def get_url(self, user):
        if self.needs_evaluation():
            return reverse('conclusion', args=[self.pk])
        if self in user.approvable_experiences() and user.is_hallstaff():
            return reverse('approval', args=[self.pk])
        if self.status == 'co' or self.start_datetime < now() and self.status == 'ad':
            return reverse('view_experience', args=[self.pk])
        return reverse('edit', args=[self.pk])

    def convert_to_dict(self, keys):
        row = model_to_dict(self, fields=keys)
        for key in row:
            if isinstance(row[key], list):
                if row[key]:
                    row[key] = ', '.join([str(a) for a in getattr(self, key).all()])
                else:
                    row[key] = "None"
            elif hasattr(self, 'get_' + key + '_display') and callable(getattr(self, 'get_' + key + '_display')):
                get_status_display = getattr(self, 'get_' + key + '_display', None)
                if get_status_display:
                    row[key] = get_status_display()
            elif not isinstance(row[key], str):
                row[key] = str(getattr(self, key))
        return row


class ExperienceApproval(models.Model):
    experience = models.ForeignKey(Experience, related_name='approval_set')
    approver = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='approval_set')
    timestamp = models.DateTimeField(default=now, blank=True)

    class Meta:
        ordering = ['timestamp']


class ExperienceComment(models.Model):
    experience = models.ForeignKey(Experience, related_name='comment_set')
    message = models.TextField()
    timestamp = models.DateTimeField(default=now)
    author = models.ForeignKey(settings.AUTH_USER_MODEL)

    class Meta:
        ordering = ['timestamp']


class EmailTask(models.Model):
    email_module = 'exdb.emails'
    package = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=100)
    users = models.ManyToManyField(settings.AUTH_USER_MODEL)
    last_sent_on = models.DateTimeField(default=now)

    def send(self, *args, **kwargs):
        module = import_module(self.email_module)
        return getattr(module, self.package)().send(self, *args, **kwargs)

    def __str__(self):
        return self.name
