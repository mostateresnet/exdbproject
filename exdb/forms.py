from django import forms
from django.core.exceptions import ValidationError
from django.utils.timezone import now
from django.utils.translation import ugettext as _
from django.forms import ModelForm
from exdb.models import Experience, ExperienceComment


class ExperienceSaveForm(ModelForm):

    class Meta:
        model = Experience
        fields = [
            'name',
            'description',
            'planners',
            'recognition',
            'start_datetime',
            'end_datetime',
            'type',
            'subtype',
            'audience',
            'attendance',
            'keywords',
            'next_approver',
            'goals',
            'guest',
            'guest_office',
            'funds',
        ]

        widgets = {
            'description': forms.Textarea(attrs={'cols': 40, 'rows': 4}),
            'goals': forms.Textarea(attrs={'cols': 40, 'rows': 4}),
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

        if not self.cleaned_data.get('description'):
            raise ValidationError(_('A description is required'))

        if not self.cleaned_data.get('end_datetime'):
            raise ValidationError(_('An end time is required'))

        if not self.cleaned_data.get('start_datetime'):
            raise ValidationError(_('A start time is required'))

        if not self.cleaned_data.get('type'):
            raise ValidationError(_('The type field is required'))

        if not self.cleaned_data.get('subtype'):
            raise ValidationError(_('The subtype field is required'))

        ex_subtype = self.cleaned_data.get('subtype')

        if not self.cleaned_data.get('next_approver') and ex_subtype.needs_verification:
            raise ValidationError(_('Please select the supervisor to review this experience'))

        if self.cleaned_data.get('start_datetime') >= self.cleaned_data.get('end_datetime'):
            raise ValidationError(_('Start time must be before end time'))

        if not ex_subtype.needs_verification and self.cleaned_data.get('start_datetime') > self.when:
            raise ValidationError(_('%(name)s experiences must have happened in the past') % {'name': ex_subtype.name})

        if ex_subtype.needs_verification and self.cleaned_data.get('start_datetime') < self.when:
            raise ValidationError(_('%(name)s events cannot happen in the past') % {'name': ex_subtype.name})

        if not ex_subtype.needs_verification and (not self.cleaned_data.get(
                'attendance') or self.cleaned_data.get('attendance') < 1):
            raise ValidationError(_('%(name)s events must have an attendance') % {'name': ex_subtype.name})

        if not ex_subtype.needs_verification and not self.cleaned_data.get('audience'):
            raise ValidationError(_('%(name)s events must have an audience') % {'name': ex_subtype.name})

        if ex_subtype.needs_verification and self.cleaned_data.get('attendance'):
            raise ValidationError(_('%(name)s events cannot have an attendance') % {'name': ex_subtype.name})

        return self.cleaned_data


class ExperienceConclusionForm(ModelForm):

    class Meta:
        model = Experience
        fields = ['attendance', 'conclusion']
        widgets = {
            'conclusion': forms.Textarea(attrs={'cols': 40, 'rows': 4}),
        }

    def clean(self):
        if not self.cleaned_data.get('attendance'):
            raise ValidationError(_('There must be an attendance'))

        if self.cleaned_data.get('attendance') < 0:
            raise ValidationError(_('There cannot be a negative attendance'))

        if not self.cleaned_data.get('conclusion'):
            raise ValidationError(_('Please enter a conclusion'))


class ApprovalForm(ModelForm):
    message = forms.CharField(widget=forms.Textarea(attrs={'cols': 40, 'rows': 4}))

    class Meta:
        model = ExperienceComment
        exclude = ['experience', 'author', 'timestamp']

    def clean(self):
        if not self.cleaned_data.get('message'):
            raise ValidationError(_('There must be a comment if the Experience is denied.'))
        return self.cleaned_data
