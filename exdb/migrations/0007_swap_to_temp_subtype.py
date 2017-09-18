# -*- coding: utf-8 -*-
# Generated by Django 1.9.10 on 2016-10-21 13:27
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    def swap_over_subtypes(apps, schema_editor):
        Experience = apps.get_model("exdb", "Experience")
        for experience in Experience.objects.all():
            experience.temp_subtypes.add(experience.subtype)

    dependencies = [
        ('exdb', '0006_experience_temp_subtypes'),
    ]

    operations = [
        migrations.RunPython(swap_over_subtypes),
    ]
