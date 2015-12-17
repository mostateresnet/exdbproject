from django.views.generic import TemplateView, ListView
from exdb.models import Experience

class WelcomeView(TemplateView):
    template_name = 'exdb/welcome.html'

class PendingApprovalQueueView(ListView):
    template_name = 'exdb/pending.html'
    context_object_name = "experiences"

    def get_queryset(self):
        return Experience.objects.filter(status='pe')
