from django.db import models
from django.utils.timezone import now
from django.conf import settings


class SubType(models.Model):
    name = models.CharField(max_length=300)

    def __str__(self):
        return self.name


class Type(models.Model):
    name = models.CharField(max_length=300)

    def __str__(self):
        return self.name


class Category(models.Model):
    name = models.CharField(max_length=300)

    def __str__(self):
        return self.name


class Audience(models.Model):
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
        ('dr', 'Draft'),
        ('pe', 'Pending'),
        ('ap', 'Approval'),
        ('de', 'Denied'),
        ('ad', 'Approved'),
        ('co', 'Completed'),
        ('ca', 'Cancelled')
    )

    author = models.ForeignKey(settings.AUTH_USER_MODEL)
    planners = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='planner_set', blank=True)
    title = models.CharField(max_length=300)
    description = models.TextField()
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    type = models.ForeignKey(Type)
    sub_type = models.ForeignKey(SubType)
    goal = models.TextField()
    keywords = models.ManyToManyField(Keyword)
    audience = models.ForeignKey(Audience)
    guest = models.CharField(max_length=300)
    guest_office = models.CharField(max_length=300)
    attendance = models.IntegerField(null=True, blank=True)
    created_datetime = models.DateTimeField(default=now, blank=True)
    recognition = models.ManyToManyField(Organization)
    status = models.CharField(max_length=2, choices=STATUS_TYPES, default=STATUS_TYPES[0][0])

    def __str__(self):
        return self.title


class ExperienceComment(models.Model):
    experience = models.ForeignKey(Experience, related_name='comment_set')
    message = models.TextField()
    timestamp = models.DateTimeField(default=now)
    author = models.ForeignKey(settings.AUTH_USER_MODEL)

    class Meta:
        ordering = ['timestamp']
