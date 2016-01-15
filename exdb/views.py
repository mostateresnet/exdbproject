from django.views.generic import TemplateView, ListView
from django.views.generic.edit import CreateView
from django.shortcuts import get_object_or_404
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from exdb.models import Experience, ExperienceComment
from exdb.forms import ApprovalForm

class WelcomeView(TemplateView):
    template_name = 'exdb/welcome.html'

class PendingApprovalQueueView(ListView):
    template_name = 'exdb/pending.html'
    context_object_name = "experiences"

    def get_queryset(self):
        return Experience.objects.filter(status='pe')

class ExperienceApprovalView(CreateView):
    template_name = 'exdb/experience_approval.html'
    form_class = ApprovalForm

    def get_success_url(self):
        return reverse('pending')

    def get_experience(self):
        return get_object_or_404(Experience, pk=self.kwargs['pk'], status='pe')

    def get_context_data(self, **kwargs):
        context = super(ExperienceApprovalView, self).get_context_data()
        context['experience'] = self.get_experience()
        context['comments'] = ExperienceComment.objects.filter(experience=context['experience'])
        return context

    def form_valid(self, form):
        form.instance.author = self.request.user
        form.instance.experience = self.get_experience()
        form.instance.experience.status = 'ad' if self.request.POST.get('approve') else 'de'
        form.instance.experience.save()
        return super(ExperienceApprovalView, self).form_valid(form)

    def form_invalid(self, form):
        if self.request.POST.get('approve'):
            experience = self.get_experience()
            experience.status = 'ad'
            experience.save()
            return HttpResponseRedirect(self.get_success_url())
        else:
            return super(ExperienceApprovalView, self).form_invalid(form)
