# -*- coding: utf-8 -*-
# Generated by Django 1.9.13 on 2022-08-16 06:53
from __future__ import unicode_literals

from django.db import migrations, models


def forwards(apps, schema_editor):

    # Generate all the new "order" values
    Section = apps.get_model('exdb', 'Section')
    for s in Section.objects.all():
        s.order = s.name.lower()
        replacements = [
            ('first', 1),
            ('second', 2),
            ('third', 3),
            ('fourth', 4),
            ('fifth', 5),
            ('sixth', 6),
            ('seventh', 7),
            ('eighth', 8),
            ('ninth', 9),
            ('tenth', 10),
            ('eleventh', 11),
            ('twelfth', 12),
            ('thirteenth', 13),
            ('fourteenth', 14),
            ('fifteenth', 15),
            ('sixteenth', 16),
            ('seventeenth', 17),
            ('eighteenth', 18),
            ('eigthteenth', 18), # don't ask
            ('nineteenth', 19),
            ('twentieth', 20),
        ]
        for pattern, substitution in replacements:
            s.order = s.order.replace(pattern, '%03d' % substitution)

        s.save()


class Migration(migrations.Migration):

    dependencies = [
        ('exdb', '0010_auto_20180206_1057'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='section',
            options={'ordering': ['order']},
        ),
        migrations.AddField(
            model_name='section',
            name='order',
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]