# -*- coding: utf-8 -*-
# Generated by Django 1.9.9 on 2016-09-23 17:12
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('exdb', '0004_auto_20160921_0909'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='Type',
            new_name='Temp',
        ),
        migrations.RenameModel(
            old_name='SubType',
            new_name='Type',
        ),
        migrations.RenameModel(
            old_name='Temp',
            new_name='Subtype',
        ),

        migrations.RenameField(
            model_name='experience',
            old_name='type',
            new_name='temp',
        ),
        migrations.RenameField(
            model_name='experience',
            old_name='sub_type',
            new_name='type',
        ),
        migrations.RenameField(
            model_name='experience',
            old_name='temp',
            new_name='subtype',
        ),
    ]
