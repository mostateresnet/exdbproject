# -*- coding: utf-8 -*-
# Generated by Django 1.9a1 on 2015-12-17 15:09
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('exdb', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='experience',
            name='audience',
            field=models.CharField(choices=[(b'b', b'Building'), (b'c', b'Campus'), (b'f', b'Floor')], max_length=2),
        ),
        migrations.DeleteModel(
            name='Audience',
        ),
    ]
