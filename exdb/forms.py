from django import forms
from django.core.exceptions import ValidationError
from django.forms import ModelForm
from django.utils.timezone import now
from exdb.models import Experience


class ExperienceSaveForm(ModelForm):

    class Meta:
        model = Experience
        fields = ['name', 'description', 'planners', 'start_datetime', 'end_datetime', 'type',
                  'sub_type', 'recognition', 'audience', 'attendance', 'keywords', 'goal', 'guest',
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
        }

    def __init__(self, *args, **kwargs):
        self.when = kwargs.pop('when', now())
        return super(ExperienceSaveForm, self).__init__(*args, **kwargs)


class ExperienceSubmitForm(ExperienceSaveForm):
    def clean(self):

        if not self.cleaned_data.get('end_datetime'):
            raise ValidationError("Need a end date!")

        if not self.cleaned_data.get('start_datetime'):
            raise ValidationError("Need a start time!")

        if not self.cleaned_data.get('sub_type'):
            raise ValidationError("Need a subType")

        if not self.cleaned_data.get('type'):
            raise ValidationError("Need a subType")

        if self.cleaned_data.get('start_datetime') >= self.cleaned_data.get('end_datetime'):
            raise ValidationError("Start date must be before end date")

        if not self.cleaned_data.get('type').needs_verification and self.cleaned_data.get('start_datetime') > self.when:
            raise ValidationError("Spontaneous experiences must have happened in the past")

        if self.cleaned_data.get('type').needs_verification and self.cleaned_data.get('start_datetime') < self.when:
            raise ValidationError("Only Spontaneous events can happen in the past")

        if not self.cleaned_data.get('type').needs_verification and not self.cleaned_data.get('attendance'):
            raise ValidationError("Spontaneous events must have an attendance")

        if not self.cleaned_data.get('type').needs_verification and not self.cleaned_data.get('audience'):
            raise ValidationError("Spontaneous events must have an attendance")

        if not self.cleaned_data.get('type').needs_verification and self.cleaned_data.get('attendance') and self.cleaned_data.get('attendance') < 1:
            raise ValidationError("Spontaneous events must have an attendance greater than 0")

        if self.cleaned_data.get('type').needs_verification and self.cleaned_data.get('attendance'):
            raise ValidationError("Future events cannot have an attendance")

        return self.cleaned_data
