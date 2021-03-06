from django.core.management.base import BaseCommand, CommandError
from exdb.models import EmailTask
from exdb import emails


class Command(BaseCommand):

    def create_email_tasks(self):
        emails_attrs = dir(emails)

        # naturally we do not want the base class
        emails_attrs.remove('EmailTaskBase')

        email_tasks = {}
        for attr in emails_attrs:
            try:
                if issubclass(getattr(emails, attr), emails.EmailTaskBase):
                    email_tasks[attr] = getattr(emails, attr)
            except TypeError:
                pass

        existing_tasks = EmailTask.objects.values_list('package', flat=True)
        email_task_database_objects = []
        for class_name, cls in email_tasks.items():
            if class_name not in existing_tasks:
                try:
                    et = EmailTask(name=cls.task_name, package=class_name)
                    email_task_database_objects.append(et)
                except AttributeError:  # pragma: no cover
                    raise AttributeError("task_name must be defined for %s" % class_name)

        created_tasks = EmailTask.objects.bulk_create(email_task_database_objects)

        self.stdout.write('%d new task(s) created out of %d total email tasks.' %
                          (len(created_tasks), len(email_tasks.keys())))

    def send_emails(self):
        tasks = EmailTask.objects.all()
        emails_sent = 0
        for task in tasks:
            emails_sent += task.send()
        self.stdout.write("%d task(s) sent %d emails" % (len(tasks), emails_sent))

    def handle(self, *args, **options):
        if options['send']:
            self.send_emails()
        if options['create']:
            self.create_email_tasks()

    def add_arguments(self, parser):
        parser.add_argument('--send',
                            action='store_true',
                            dest='send',
                            default=False,
                            help='Send all the emails for each email task.')
        parser.add_argument('--create',
                            action='store_true',
                            dest='create',
                            help='Create email task that are specified in the emails.py file.')
