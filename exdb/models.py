from importlib import import_module
from django.db import models
from django.utils.timezone import now
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.core.validators import validate_email
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey


class SubType(models.Model):
    name = models.CharField(max_length=300)

    def __str__(self):
        return self.name


class Type(models.Model):
    name = models.CharField(max_length=300)
    needs_verification = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Organization(models.Model):
    name = models.CharField(max_length=300)

    def __str__(self):
        return self.name


class Keyword(models.Model):
    name = models.CharField(max_length=300)

    def __str__(self):
        return self.name


class Experience(models.Model):
    STATUS_TYPES = (
        ('de', _('Denied')),
        ('dr', _('Draft')),
        ('pe', _('Pending Approval')),
        ('ad', _('Approved')),
        ('co', _('Completed')),
        ('ca', _('Cancelled'))
    )

    AUDIENCE_TYPES = (
        ('b', _('Building')),
        ('c', _('Campus')),
        ('f', _('Floor')),
    )

    author = models.ForeignKey(settings.AUTH_USER_MODEL)
    planners = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='planner_set', blank=True)
    name = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    type = models.ForeignKey(Type)
    sub_type = models.ForeignKey(SubType)
    goal = models.TextField(blank=True)
    keywords = models.ManyToManyField(Keyword, blank=True)
    audience = models.CharField(max_length=1, choices=AUDIENCE_TYPES, blank=True)
    guest = models.CharField(max_length=300, blank=True)
    guest_office = models.CharField(max_length=300, blank=True)
    attendance = models.IntegerField(null=True, blank=True)
    created_datetime = models.DateTimeField(default=now, blank=True)
    recognition = models.ManyToManyField(Organization, blank=True)
    status = models.CharField(max_length=2, choices=STATUS_TYPES, default=STATUS_TYPES[1][0])
    next_approver = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True, related_name='approval_queue')
    conclusion = models.TextField(blank=True)
    needs_author_email = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    def needs_evaluation(self):
        return self.status == 'ad' and self.end_datetime <= now()


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


class Email(models.Model):
    addr = models.EmailField(validators=[validate_email], unique=True, blank=False)
    related_content_type = models.ForeignKey(ContentType, null=True, blank=True)
    related_object_id = models.PositiveIntegerField(null=True)
    related_content_object = GenericForeignKey('related_content_type', 'related_object_id')

    def __str__(self):
        return self.addr


class EmailTask(models.Model):
    email_module = 'exdb.emails'
    package = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=100)
    emails = models.ManyToManyField(Email)
    last_sent_on = models.DateTimeField(default=now)

    def send(self, *args, **kwargs):
        module = import_module(self.email_module)
        return getattr(module, self.package)().send(self, *args, **kwargs)

    def sync_addrs(self):
        module = import_module(self.email_module)
        return getattr(module, self.package)().sync_addrs(self)

    def __str__(self):
        return self.name
