from datetime import datetime
from django import forms
from django.core.exceptions import ValidationError
from django.utils.timezone import now
from django.utils.translation import ugettext as _
from django.forms import ModelForm
from django.utils.timezone import utc
from exdb.models import Experience, ExperienceComment


class ExperienceSaveForm(ModelForm):

    class Meta:
        model = Experience
        fields = [
            'name',
            'description',
            'planners',
            'start_datetime',
            'end_datetime',
            'type',
            'sub_type',
            'recognition',
            'audience',
            'attendance',
            'keywords',
            'next_approver',
            'goal',
            'guest',
            'guest_office',
        ]

        widgets = {
            'description': forms.Textarea(attrs={'cols': 40, 'rows': 4}),
            'goal': forms.Textarea(attrs={'cols': 40, 'rows': 4}),
            'start_datetime': forms.SelectDateWidget(),
            'end_datetime': forms.SelectDateWidget(),
        }

        labels = {
            'start_datetime': 'Start Time',
            'end_datetime': 'End Time',
            'next_approver': 'Supervisor',
        }

    def __init__(self, *args, **kwargs):
        when = kwargs.pop('when', now())
        super(ExperienceSaveForm, self).__init__(*args, **kwargs)
        self.when = when


class ExperienceSubmitForm(ExperienceSaveForm):

    def clean(self):
        ex_type = self.cleaned_data.get('type')
        name = "" if not ex_type else ex_type.name
        min_dt = datetime.min.replace(tzinfo=utc)
        max_dt = datetime.max.replace(tzinfo=utc)

        # conditions format (validation_check, validation_error),
        conditions = (
            (not self.cleaned_data.get('description'), ValidationError(_('A description is required'))),
            (not self.cleaned_data.get('end_datetime'), ValidationError(_('An end time is required'))),
            (not self.cleaned_data.get('start_datetime'), ValidationError(_('A start time is required'))),
            (not self.cleaned_data.get('sub_type'), ValidationError(_('The sub type field is required'))),
            (not ex_type, ValidationError(_('The type field is required'))),
            (ex_type and (not self.cleaned_data.get('next_approver') and ex_type.needs_verification),
             ValidationError(_('Please select the supervisor to review this experience'))),
            (self.cleaned_data.get('start_datetime', max_dt) >= self.cleaned_data.get('end_datetime', min_dt),
             ValidationError(_('Start time must be before end time'))),
            ((ex_type and not ex_type.needs_verification) and (self.cleaned_data.get('start_datetime', max_dt) > self.when),
             ValidationError(_('%(name)s experiences must have happened in the past') % {'name': name})),
            ((ex_type and not ex_type.needs_verification) and (not self.cleaned_data.get(
                'attendance') or self.cleaned_data.get('attendance') < 1),
             ValidationError(_('%(name)s events must have an attendance') % {'name': name})),
            (ex_type and not ex_type.needs_verification and not self.cleaned_data.get('audience'),
             ValidationError(_('%(name)s events must have an audience') % {'name': name})),
            (ex_type and ex_type.needs_verification and self.cleaned_data.get('attendance'),
             ValidationError(_('%(name)s events cannot have an attendance') % {'name': name})),
            (ex_type and ex_type.needs_verification and self.cleaned_data.get('start_datetime', min_dt) < self.when,
             ValidationError(_('%(name)s events cannot happen in the past') % {'name': name})),
        )

        validation_errors = []
        for condition, invalid in conditions:
            if condition:
                validation_errors.append(invalid)

        if validation_errors:
            raise ValidationError(validation_errors)

        return self.cleaned_data


class ExperienceConclusionForm(ModelForm):

    class Meta:
        model = Experience
        fields = ['attendance', 'conclusion']
        widgets = {
            'conclusion': forms.Textarea(attrs={'cols': 40, 'rows': 4}),
        }

    def clean(self):
        conditions = (
            (not self.cleaned_data.get('attendance'), ValidationError(_('There must be an attendance'))),
            (self.cleaned_data.get('attendance') and self.cleaned_data.get('attendance') < 0,
             ValidationError(_('There cannot be a negative attendance'))),
            (not self.cleaned_data.get('conclusion'), ValidationError(_('Please enter a conclusion'))),
        )

        validation_errors = []
        for condition, invalid in conditions:
            if condition:
                validation_errors.append(invalid)

        if validation_errors:
            raise ValidationError(validation_errors)

        return self.cleaned_data


class ApprovalForm(ModelForm):
    message = forms.CharField(widget=forms.Textarea(attrs={'cols': 40, 'rows': 4}))

    class Meta:
        model = ExperienceComment
        exclude = ['experience', 'author', 'timestamp']

    def clean(self):
        if not self.cleaned_data.get('message'):
            raise ValidationError(_('There must be a comment if the Experience is denied.'))
        return self.cleaned_data
