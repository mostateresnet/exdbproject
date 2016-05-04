from django import forms
from django.core.exceptions import ValidationError
from django.utils.timezone import now
from django.utils.encoding import force_text
from django.utils.safestring import mark_safe
from django.utils.html import format_html
from django.utils.translation import ugettext as _
from django.forms import ModelForm
from exdb.models import Experience, ExperienceComment


class TypeSelect(forms.Select):

    def render_option(self, selected_choices, option_value, option_label):
        if option_value is None:
            option_value = ''  # pragma: no cover
        option_value = force_text(option_value)
        if option_value in selected_choices:
            selected_html = mark_safe(' selected="selected"')
            if not self.allow_multiple_selected:
                selected_choices.remove(option_value)
        else:
            selected_html = ''
        css_class = []
        choice_dict = {str(c.pk): c for c in self.choices.queryset}
        if option_value in choice_dict and not choice_dict[option_value].needs_verification:
            css_class.append('no-verification ')
        return format_html('<option class="{}" value="{}"{}>{}</option>',
                           ''.join(css_class),
                           option_value,
                           selected_html,
                           force_text(option_label))


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
            'conclusion'
        ]

        widgets = {
            'description': forms.Textarea(attrs={'cols': 40, 'rows': 4}),
            'goal': forms.Textarea(attrs={'cols': 40, 'rows': 4}),
            'start_datetime': forms.SelectDateWidget(),
            'end_datetime': forms.SelectDateWidget(),
            'type': TypeSelect(),
            'conclusion': forms.Textarea(attrs={'cols': 40, 'rows': 4}),
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

        if not self.cleaned_data.get('sub_type'):
            raise ValidationError(_('The sub type field is required'))

        if not self.cleaned_data.get('type'):
            raise ValidationError(_('The type field is required'))

        ex_type = self.cleaned_data.get('type')

        if not self.cleaned_data.get('next_approver') and ex_type.needs_verification:
            raise ValidationError(_('Please select the supervisor to review this experience'))

        if self.cleaned_data.get('start_datetime') >= self.cleaned_data.get('end_datetime'):
            raise ValidationError(_('Start time must be before end time'))

        if not ex_type.needs_verification and self.cleaned_data.get('start_datetime') > self.when:
            raise ValidationError(_('%(name)s experiences must have happened in the past') % {'name': ex_type.name})

        if ex_type.needs_verification and self.cleaned_data.get('start_datetime') < self.when:
            raise ValidationError(_('%(name)s events cannot happen in the past') % {'name': ex_type.name})

        if not ex_type.needs_verification and (not self.cleaned_data.get(
                'attendance') or self.cleaned_data.get('attendance') < 1):
            raise ValidationError(_('%(name)s events must have an attendance') % {'name': ex_type.name})

        if not ex_type.needs_verification and not self.cleaned_data.get('audience'):
            raise ValidationError(_('%(name)s events must have an audience') % {'name': ex_type.name})

        if ex_type.needs_verification and self.cleaned_data.get('attendance'):
            raise ValidationError(_('%(name)s events cannot have an attendance') % {'name': ex_type.name})

        # There are too many branches in this function; this is fixed on
        # the approval validation branch.
        if not ex_type.needs_verification and not self.cleaned_data.get('conclusion'):
            raise ValidationError(_('%(name)s events must have a conclusion') % {'name': ex_type.name})

        if ex_type.needs_verification and self.cleaned_data.get('conclusion'):
            self.cleaned_data['conclusion'] = ""

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
