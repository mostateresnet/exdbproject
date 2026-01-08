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
from django.contrib.auth import get_user_model
from exdb.models import Experience, ExperienceComment, Type, Subtype


class TypeSelect(forms.Select):
    def render_option(self, selected_choices, option_value, option_label):
        if option_value is None:
            option_value = ''  # pragma: no cover
        option_value = force_text(option_value)
        if option_value in selected_choices:
            selected_html = mark_safe(' selected="selected"')
            if not self.allow_multiple_selected:
                # Only allow for a single selection.
                selected_choices.remove(option_value)
        else:
            selected_html = ''
        valid_subtypes = []
        choice_dict = {str(c.pk): c for c in self.choices.queryset}
        if option_value in choice_dict:
            valid_subtypes = [st.pk for st in choice_dict[option_value].valid_subtypes.all()]
        return format_html('<option data-valid-subtypes="{}" value="{}"{}>{}</option>',
                           ','.join(str(pk) for pk in valid_subtypes),
                           option_value,
                           selected_html,
                           force_text(option_label))


class SubtypeRenderer(forms.widgets.CheckboxFieldRenderer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.choice_object_dict = {st.pk: st for st in Subtype.objects.filter(pk__in=[c[0] for c in self.choices])}

    def choice_input_class(self, name, value, attrs, choice, index):
        if choice[0] in self.choice_object_dict and not self.choice_object_dict[choice[0]].needs_verification:
            class_attr = 'no-verification'
        else:
            class_attr = 'verification'
        attrs = attrs.copy()
        attrs['class'] = class_attr
        return forms.widgets.CheckboxChoiceInput(name, value, attrs, choice, index)


class SubtypeSelect(forms.CheckboxSelectMultiple):
    renderer = SubtypeRenderer


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
            'type': TypeSelect(),
            'subtypes': SubtypeSelect(),
            'conclusion': forms.Textarea(attrs={'cols': 40, 'rows': 4}),
        }

        labels = {
            'start_datetime': _('Starting Date & Time'),
            'end_datetime': _('Ending Date & Time'),
            'next_approver': _('Supervisor'),
            'name': _('Title'),
        }

    def __init__(self, *args, **kwargs):
        when = kwargs.pop('when', now())
        submit = kwargs.pop('submit', None)
        super(ExperienceSaveForm, self).__init__(*args, **kwargs)
        self.when = when
        self.approval_form = submit
        self.fields['type'].queryset = Type.objects.prefetch_related('valid_subtypes')
        self.fields['next_approver'].queryset = get_user_model().objects.hallstaff()
        self.fields['planners'].queryset = get_user_model().objects.filter(is_active=True)

        # --- Add Help Texts for Subtypes ---
        subtype_help_map = {
            "Alcohol/Alcohol Alternative": "Programs addressing alcohol awareness or providing non-alcoholic social options.",
            "Building-wide Community Enrichment": "Events open to everyone in the building that build community and belonging.",
            "Bulletin Board": "Informational or themed bulletin boards created to educate or engage residents.",
            "Door Decorations": "Creative decorations for residents’ doors to promote community identity.",
            "Floor Decorations": "Shared floor decorations to enhance community spirit or theme.",
            "LLC": "Living-Learning Community–related experience connecting academic and residential life.",
            "Needs-based": "Program created to respond to a specific community need or incident.",
            "Other Planned Community Development Experience": "An event that doesn’t fit standard categories but is intentionally planned.",
            "Passive Engagement Campaign": "Educational or engagement efforts not requiring active participation (e.g., posters).",
            "Piggyback (does not fit another category)": "Small-scale event added to an existing program or initiative.",
            "Public Affairs": "Events focused on current issues, politics, or civic engagement.",
            "Resource": "Efforts to share or promote available campus/community resources.",
            "Sexual Misconduct Education and Prevention": "Programs promoting awareness and prevention of sexual misconduct.",
            "Spontaneous": "Unplanned or casual community interactions that still have impact.",
            "Support": "Programs aimed at offering emotional, academic, or social support.",
            "Sustainability": "Events that promote eco-friendly behaviors and environmental responsibility.",
            "Togetherness": "Community-building activities that strengthen relationships and inclusion.",
        }

        # Customize subtype labels with help text underneath
        subtype_choices = []
        for subtype in Subtype.objects.all():
            helptext = subtype_help_map.get(subtype.name, "")
            label_html = format_html(
                '<div class="subtype-label">'
                '<span class="subtype-name">{}</span><br>'
                '<small class="subtype-help">{}</small>'
                '</div>', subtype.name, helptext
            )
            subtype_choices.append((subtype.pk, mark_safe(label_html)))

        self.fields['subtypes'].choices = subtype_choices


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
            (needs_verification and (self.cleaned_data.get('start_datetime', min_dt) < self.when and not self.approval_form),
                ValidationError(_('This experience must have a start date in the future'))),
            (self.cleaned_data.get('start_datetime', max_dt) >= self.cleaned_data.get('end_datetime', min_dt),
             ValidationError(_('Start time must be before end time'))),
            (needs_verification is False and ((not self.cleaned_data.get(
                'attendance') and self.cleaned_data.get('attendance', -1) != 0)
             or self.cleaned_data.get('attendance') < 0),
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
            (not self.cleaned_data.get('attendance') and self.cleaned_data.get('attendance', -1) != 0,
             ValidationError(_('There must be an attendance'))),
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
