from collections import OrderedDict
from django.views.generic import TemplateView, ListView
from django.views.generic.edit import CreateView, UpdateView
from django.shortcuts import get_object_or_404
from django.core.urlresolvers import reverse
from django.contrib import auth
from django.http import HttpResponseRedirect
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth import get_user_model
from django.db.models import Q

from exdb.models import Experience, ExperienceComment, ExperienceApproval
from .forms import ExperienceSubmitForm, ExperienceSaveForm, ApprovalForm, ExperienceConclusionForm


class WelcomeView(TemplateView):
    access_level = 'basic'
    template_name = 'exdb/welcome.html'


class CreateExperienceView(CreateView):
    access_level = 'basic'
    model = Experience
    template_name = 'exdb/create_experience.html'

    def get_success_url(self):
        return reverse('home')

    def form_valid(self, form):
        form.instance.author = self.request.user

        if 'submit' in self.request.POST:
            if form.instance.type.needs_verification:
                form.instance.status = 'pe'
            else:
                form.instance.status = 'co'
        elif 'save' in self.request.POST:
            form.instance.status = 'dr'
        return super(CreateExperienceView, self).form_valid(form)

    def get_form_class(self):
        if self.request.method.upper() == 'POST' and 'submit' in self.request.POST:
            return ExperienceSubmitForm
        else:
            return ExperienceSaveForm


class HallStaffDashboardView(ListView):
    acess_leve = 'basic'
    template_name = 'exdb/home.html'
    context_object_name = 'experiences'

    def get_queryset(self):
        experience_approvals = ExperienceApproval.objects.filter(
            approver=self.request.user, experience__status='ad')
        experiences = Experience.objects.filter(Q(next_approver=self.request.user) | Q(
            pk__in=experience_approvals.values('experience')))
        return experiences

    def get_context_data(self):
        context = super(HallStaffDashboardView, self).get_context_data()
        context['user'] = self.request.user

        status_to_display = [_('Pending Approval'), _('Needs Evaluation'), _('Approved')]
        experience_dict = OrderedDict()
        for status in status_to_display:
            experience_dict[status] = []
        for experience in context[self.context_object_name]:
            if experience.needs_evaluation():
                experience_dict[_('Needs Evaluation')].append(experience)
            else:
                if experience.get_status_display() in experience_dict:
                    experience_dict[experience.get_status_display()].append(experience)
        context['experience_dict'] = experience_dict

        one_month = timezone.now() + timezone.timedelta(days=31)
        upcoming = []
        for experience in context['experience_dict'][_('Approved')]:
            if experience.start_datetime > timezone.now() and experience.start_datetime < one_month:
                upcoming.append(experience)
        context['upcoming'] = upcoming
        return context


class RAHomeView(ListView):
    template_name = 'exdb/home.html'
    access_level = 'basic'
    context_object_name = 'experiences'

    def get_queryset(self):
        return Experience.objects.filter(author=self.request.user).order_by('created_datetime')

    def get_context_data(self, *args, **kwargs):
        context = super(RAHomeView, self).get_context_data(*args, **kwargs)
        context['user'] = self.request.user

        experience_dict = OrderedDict()
        experience_dict[_('Needs Evaluation')] = []
        for status in Experience.STATUS_TYPES:
            experience_dict[status[1]] = []
        for experience in context[self.context_object_name]:
            if experience.needs_evaluation():
                experience_dict[_('Needs Evaluation')].append(experience)
            else:
                experience_dict[experience.get_status_display()].append(experience)
        context['experience_dict'] = experience_dict

        one_week = timezone.now() + timezone.timedelta(days=7)
        upcoming = []
        for experience in context['experience_dict'][_('Approved')]:
            if experience.start_datetime > timezone.now() and experience.start_datetime < one_week:
                upcoming.append(experience)
        context['upcoming'] = upcoming
        return context


class HomeView(ListView):
    access_level = 'basic'
    hall_staff_view = staticmethod(HallStaffDashboardView.as_view())
    ra_view = staticmethod(RAHomeView.as_view())

    def dispatch(self, request, *args, **kwargs):
        if self.request.user.groups.filter(name='hs'):
            return self.hall_staff_view(request, *args, **kwargs)
        else:
            return self.ra_view(request, *args, **kwargs)


class ExperienceApprovalView(CreateView):
    access_level = 'basic'
    template_name = 'exdb/experience_approval.html'
    form_class = ApprovalForm

    def get_experience(self):
        return get_object_or_404(Experience, pk=self.kwargs['pk'], status='pe', next_approver=self.request.user)

    def get_success_url(self):
        return reverse('home')

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
            form.instance.experience.next_approver = None
            ExperienceApproval.objects.create(
                experience=form.instance.experience,
                approver=self.request.user
            )
        form.instance.experience.save()
        return super(ExperienceApprovalView, self).form_valid(form)

    def form_invalid(self, form):
        if self.request.POST.get('approve'):
            experience = self.get_experience()
            experience.next_approver = None
            experience.status = 'ad'
            experience.save()
            ExperienceApproval.objects.create(experience=experience,
                                              approver=self.request.user)
            return HttpResponseRedirect(self.get_success_url())
        else:
            return super(ExperienceApprovalView, self).form_invalid(form)


class ExperienceConclusionView(UpdateView):
    access_level = 'basic'
    template_name = 'exdb/conclusion.html'
    form_class = ExperienceConclusionForm
    model = Experience

    def get_success_url(self):
        return reverse('home')

    def get_queryset(self, **kwargs):
        return Experience.objects.filter(pk=self.kwargs['pk'])

    def form_valid(self, form):
        valid_form = super(ExperienceConclusionView, self).form_valid(form)
        experience = get_object_or_404(Experience, pk=self.kwargs['pk'])
        experience.status = 'co'
        experience.save()
        return valid_form


class ViewExperienceView(TemplateView):
    access_level = 'basic'
    template_name = 'exdb/experience_view.html'

    def get_context_data(self, **kwargs):
        context = super(ViewExperienceView, self).get_context_data()
        context['experience'] = get_object_or_404(Experience, pk=self.kwargs['pk'])
        return context
