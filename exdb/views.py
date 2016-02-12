from collections import OrderedDict
from django.views.generic import TemplateView, ListView
from django.views.generic.edit import CreateView
from django.shortcuts import get_object_or_404
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.utils.timezone import now
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from exdb.models import Experience, ExperienceComment
from .forms import ExperienceSubmitForm, ExperienceSaveForm, ApprovalForm


class WelcomeView(TemplateView):
    template_name = 'exdb/welcome.html'


class CreateExperienceView(CreateView):
    model = Experience
    template_name = 'exdb/create_experience.html'

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


class RAHomeView(ListView):
    template_name = 'exdb/ra_home.html'
    context_object_name = 'experiences'

    def get_queryset(self):
        return Experience.objects.filter(author=self.request.user).order_by('created_datetime')

    def get_context_data(self, *args, **kwargs):
        context = super(RAHomeView, self).get_context_data(*args, **kwargs)
        context['ra'] = self.request.user

        experience_dict = OrderedDict()
        for status in Experience.STATUS_TYPES:
            experience_dict[status[1]] = []
        for experience in context[self.context_object_name]:
            experience_dict[experience.get_status_display()].append(experience)
        context['experience_dict'] = experience_dict

        one_week = timezone.now() + timezone.timedelta(days=7)
        week_ahead = []
        for experience in context['experience_dict'][_('Approved')]:
            if experience.start_datetime > timezone.now() and experience.start_datetime < one_week:
                week_ahead.append(experience)
        context['week_ahead'] = week_ahead
        return context


class ExperienceApprovalView(CreateView):
    template_name = 'exdb/experience_approval.html'
    form_class = ApprovalForm

    def get_experience(self):
        return get_object_or_404(Experience, pk=self.kwargs['pk'], status='pe')

    def get_success_url(self):
        return reverse('pending')

    def get_context_data(self, **kwargs):
        context = super(ExperienceApprovalView, self).get_context_data()
        context['experience'] = self.get_experience()
        context['comments'] = ExperienceComment.objects.filter(experience=context['experience'])
        return context

    def form_valid(self, form):
        form.instance.author = self.request.user
        form.instance.experience = self.get_experience()
        form.instance.experience.status = 'ad' if self.request.POST.get('approve') else 'de'
        if form.instance.experience.status == 'ad':
            form.instance.experience.approver = self.request.user
            form.instance.experience.approved_timestamp = now()
        form.instance.experience.save()
        return super(ExperienceApprovalView, self).form_valid(form)

    def form_invalid(self, form):
        if self.request.POST.get('approve'):
            experience = self.get_experience()
            experience.approver = self.request.user
            experience.approved_timestamp = now()
            experience.status = 'ad'
            experience.save()
            return HttpResponseRedirect(self.get_success_url())
        else:
            return super(ExperienceApprovalView, self).form_invalid(form)
