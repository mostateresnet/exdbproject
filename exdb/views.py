from django.views.generic import TemplateView, ListView
from django.shortcuts import get_object_or_404
from exdb.models import Experience

class WelcomeView(TemplateView):
    template_name = 'exdb/welcome.html'

class PendingApprovalQueueView(ListView):
    template_name = 'exdb/pending.html'
    context_object_name = "experiences"

    def get_queryset(self):
        return Experience.objects.filter(status='pe')

class ExperienceApprovalView(ListView):
    template_name = 'exdb/experience_approval.html'
    context_object_name = 'experience'

    def get_queryset(self):
        exp = get_object_or_404(Experience, pk=self.kwargs['pk'])
        return exp
