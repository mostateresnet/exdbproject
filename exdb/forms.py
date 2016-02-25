from django import forms
from django.core.exceptions import ValidationError
from django.utils.timezone import now
from django.forms import ModelForm
from exdb.models import Experience, ExperienceComment


class ExperienceSaveForm(ModelForm):

    class Meta:
        model = Experience
        fields = ['name', 'description', 'planners', 'start_datetime', 'end_datetime', 'type',
                  'sub_type', 'recognition', 'audience', 'attendance', 'keywords', 'next_approver', 'goal', 'guest',
                  'guest_office']

        widgets = {
            'description': forms.Textarea(attrs={'cols': 40, 'rows': 4}),
            'goal': forms.Textarea(attrs={'cols': 40, 'rows': 4}),
            'start_datetime': forms.SelectDateWidget(),
            'end_datetime': forms.SelectDateWidget(),
        }

        labels = {
            'start_datetime': 'Start Time',
            'end_datetime': 'End Time',
            'next_approver': 'Suprivisor',
        }

    def __init__(self, *args, **kwargs):
        when = kwargs.pop('when', now())
        super(ExperienceSaveForm, self).__init__(*args, **kwargs)
        self.when = when


class ExperienceSubmitForm(ExperienceSaveForm):

    def clean(self):

        if not self.cleaned_data.get('end_datetime'):
            raise ValidationError("An end time is required")

        if not self.cleaned_data.get('start_datetime'):
            raise ValidationError("A start time is required")

        if not self.cleaned_data.get('sub_type'):
            raise ValidationError("The sub type field is required")

        if not self.cleaned_data.get('type'):
            raise ValidationError("The type field is required")

        ex_type = self.cleaned_data.get('type')

        if self.cleaned_data.get('start_datetime') >= self.cleaned_data.get('end_datetime'):
            raise ValidationError("Start time must be before end time")

        if not ex_type.needs_verification and self.cleaned_data.get('start_datetime') > self.when:
            raise ValidationError(ex_type.name + " experiences must have happened in the past")

        if ex_type.needs_verification and self.cleaned_data.get('start_datetime') < self.when:
            raise ValidationError(ex_type.name + " events cannot happen in the past")

        if not ex_type.needs_verification and not self.cleaned_data.get('attendance'):
            raise ValidationError(ex_type.name + " events must have an attendance")

        if not ex_type.needs_verification and not self.cleaned_data.get('audience'):
            raise ValidationError(ex_type.name + " events must have an audience")

        if not ex_type.needs_verification and self.cleaned_data.get(
                'attendance') and self.cleaned_data.get('attendance') < 1:
            raise ValidationError(ex_type.name + " events must have an attendance greater than 0")

        if ex_type.needs_verification and self.cleaned_data.get('attendance'):
            raise ValidationError(ex_type.name + " events cannot have an attendance")

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
            raise ValidationError("There must be an attendance")

        if self.cleaned_data.get('attendance') < 0:
            raise ValidationError("There cannot be a negative attendance")

        if not self.cleaned_data.get('conclusion'):
            raise ValidationError("Please enter a conclusion")


class ApprovalForm(ModelForm):
    message = forms.CharField(widget=forms.Textarea(attrs={'cols': 40, 'rows': 4}))

    class Meta:
        model = ExperienceComment
        exclude = ['experience', 'author', 'timestamp']
