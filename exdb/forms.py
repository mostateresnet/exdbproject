from datetime import datetime
from django import forms
from django.core.exceptions import ValidationError
from django.utils.timezone import now
from django.utils.encoding import force_text
from django.utils.safestring import mark_safe
from django.utils.html import format_html
from django.utils.translation import ugettext as _
from django.forms import ModelForm
from django.utils.timezone import utc
from exdb.models import Experience, ExperienceComment


class SubtypeSelect(forms.SelectMultiple):

    def render_option(self, selected_choices, option_value, option_label):
        if option_value is None:
            option_value = ''  # pragma: no cover
        option_value = force_text(option_value)
        if option_value in selected_choices:
            selected_html = mark_safe(' selected="selected"')

        else:
            selected_html = ''
        css_classes = []
        choice_dict = {str(c.pk): c for c in self.choices.queryset}
        if option_value in choice_dict and not choice_dict[option_value].needs_verification:
            css_classes.append('no-verification')
        else:
            css_classes.append('verification')
        return format_html('<option class="{}" value="{}"{}>{}</option>',
                           ' '.join(css_classes),
                           option_value,
                           selected_html,
                           force_text(option_label))


class ExperienceSaveForm(ModelForm):

    class Meta:
        model = Experience
        fields = [
            'name',
            'type',
            'subtypes',
            'description',
            'goals',
            'planners',
            'recognition',
            'start_datetime',
            'end_datetime',
            'audience',
            'attendance',
            'keywords',
            'next_approver',
            'guest',
            'guest_office',
            'funds',
            'conclusion',
        ]

        widgets = {
            'description': forms.Textarea(attrs={'cols': 40, 'rows': 4}),
            'goals': forms.Textarea(attrs={'cols': 40, 'rows': 4}),
            'subtypes': SubtypeSelect(),
            'conclusion': forms.Textarea(attrs={'cols': 40, 'rows': 4}),
        }

        labels = {
            'start_datetime': 'Start Time',
            'end_datetime': 'End Time',
            'next_approver': 'Supervisor',
            'name': 'Title',
        }

    def __init__(self, *args, **kwargs):
        when = kwargs.pop('when', now())
        submit = kwargs.pop('submit', None)
        super(ExperienceSaveForm, self).__init__(*args, **kwargs)
        self.when = when
        self.approval_form = submit


class ExperienceSubmitForm(ExperienceSaveForm):

    def clean(self):
        ex_subtype = self.cleaned_data.get('subtypes')
        needs_verification = True

        if ex_subtype:
            needs_verification = any(x.needs_verification for x in ex_subtype)

        min_dt = datetime.min.replace(tzinfo=utc)
        max_dt = datetime.max.replace(tzinfo=utc)

        # conditions format (validation_check, validation_error),
        conditions = (
            (not self.cleaned_data.get('description'), ValidationError(_('A description is required'))),
            (not self.cleaned_data.get('end_datetime'), ValidationError(_('An end time is required'))),
            (not self.cleaned_data.get('start_datetime'), ValidationError(_('A start time is required'))),
            (not self.cleaned_data.get('type'), ValidationError(_('The type field is required'))),
            (not ex_subtype, ValidationError(_('The subtype field is required'))),
            (needs_verification and not self.approval_form and
                not self.cleaned_data.get('next_approver'),
             ValidationError(_('Please select the supervisor to review this experience'))),
            (needs_verification is False and (self.cleaned_data.get('start_datetime', max_dt) > self.when),
                ValidationError(_('This experience must have a start date in the past'))),
            (needs_verification and (self.cleaned_data.get('start_datetime', max_dt) < self.when),
                ValidationError(_('This experience must have a start date in the future'))),
            (self.cleaned_data.get('start_datetime', max_dt) >= self.cleaned_data.get('end_datetime', min_dt),
             ValidationError(_('Start time must be before end time'))),
            (needs_verification is False and (not self.cleaned_data.get(
                'attendance') or self.cleaned_data.get('attendance') < 1),
             ValidationError(_('An attendance is required'))),
            (needs_verification is False and not self.cleaned_data.get('audience'),
             ValidationError(_('An audience is required'))),
            (needs_verification and self.cleaned_data.get('attendance'),
             ValidationError(_('An attendance is not allowed yet'))),
            (needs_verification and self.cleaned_data.get('next_approver')
                and not self.cleaned_data.get('next_approver').is_hallstaff(),
             ValidationError(_('Supervisor must have permissions to approve and deny experiences'))),
            (needs_verification is False and not self.cleaned_data.get('conclusion'),
             ValidationError(_('A conclusion is required'))),
        )

        validation_errors = []
        for condition, invalid in conditions:
            if condition:
                validation_errors.append(invalid)

        if validation_errors:
            raise ValidationError(validation_errors)

        # If user passes conclusion and exp needs verification
        # Remove the conclusion since the experience hasn't happened yet.
        if needs_verification and self.cleaned_data.get('conclusion'):
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
