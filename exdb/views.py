from django.views.generic import TemplateView
from django.views.generic.edit import CreateView
from django.core.urlresolvers import reverse
from django.utils import timezone

from .models import Experience
from .forms import ExperienceForm

class WelcomeView(TemplateView):
    template_name = 'exdb/welcome.html'



class CreateExperienceView(CreateView):
    model = Experience
    template_name = 'exdb/create-experience.html'
    form_class = ExperienceForm

    def get_success_url(self):
        return reverse('welcome')

    def form_valid(self, form):
        form.instance.author = self.request.user

        # If the experience is spontaneous skip verification and go strait to completed.
        if(form.instance.type.needs_verification):
            form.instance.status = 'dr'
        else:
            form.instance.status = 'co'
            form.instance.approver = self.request.user
            form.instance.approved_timestamp = timezone.now()
        return super(CreateExperienceView, self).form_valid(form)
