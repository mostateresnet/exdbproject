from django.db import models
from django.utils.timezone import now
from django.conf import settings


class SubType(models.Model):
    name = models.CharField(max_length=300)

    def __str__(self):
        return self.name


class Type(models.Model):
    name = models.CharField(max_length=300)
    needs_verification = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Category(models.Model):
    name = models.CharField(max_length=300)

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
        ('de', 'Denied'),
        ('dr', 'Draft'),
        ('pe', 'Pending Approval'),
        ('ad', 'Approved'),
        ('co', 'Completed'),
        ('ca', 'Cancelled')
    )

    AUDIENCE_TYPES = (
        ('b', 'Building'),
        ('c', 'Campus'),
        ('f', 'Floor'),
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
    status = models.CharField(max_length=2, choices=STATUS_TYPES, default=STATUS_TYPES[0][0])
    approved_timestamp = models.DateTimeField(blank=True, null=True)
    approver = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True, related_name="approver")

    def __str__(self):
        return self.name


class ExperienceComment(models.Model):
    experience = models.ForeignKey(Experience, related_name='comment_set')
    message = models.TextField()
    timestamp = models.DateTimeField(default=now)
    author = models.ForeignKey(settings.AUTH_USER_MODEL)

    class Meta:
        ordering = ['timestamp']
