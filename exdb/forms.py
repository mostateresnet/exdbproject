from django import forms
from django.core.exceptions import ValidationError
from django.forms import ModelForm

from exdb.models import ExperienceComment

class ApprovalForm(ModelForm):
    message = forms.CharField(widget=forms.Textarea(attrs={'cols': 40, 'rows': 4}))
    class Meta:
        model = ExperienceComment
        exclude = ['experience', 'author', 'timestamp']

