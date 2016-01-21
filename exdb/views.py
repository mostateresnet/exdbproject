from django.views.generic import TemplateView, ListView
from django.views.generic.edit import CreateView
from django.core.urlresolvers import reverse
from django.utils import timezone

from exdb.models import Experience
from .forms import ExperienceSubmitForm, ExperienceSaveForm


class WelcomeView(TemplateView):
    template_name = 'exdb/welcome.html'


class CreateExperienceView(CreateView):
    model = Experience
    template_name = 'exdb/create-experience.html'

    def get_success_url(self):
        return reverse('welcome')

    def form_valid(self, form):
        form.instance.author = self.request.user

        if 'submit' in self.request.POST:
            if form.instance.type.needs_verification:
                form.instance.status = 'pe'
            else:
                form.instance.status = 'co'
                form.instance.approver = self.request.user
                form.instance.approved_timestamp = timezone.now()
        elif 'save' in self.request.POST:
            form.instance.status = 'dr'
        return super(CreateExperienceView, self).form_valid(form)

    def get_form_class(self):
        if self.request.method.upper() == 'POST' and 'submit' in self.request.POST:
            return ExperienceSubmitForm
        else:
            return ExperienceSaveForm


class PendingApprovalQueueView(ListView):
    template_name = 'exdb/pending.html'
    context_object_name = "experiences"

    def get_queryset(self):
        return Experience.objects.filter(status='pe')
