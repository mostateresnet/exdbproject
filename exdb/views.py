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
        return reverse('welcome')

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


class HallStaffDashboardView(TemplateView):
    access_level = 'basic'
    template_name = 'exdb/hallstaff_dash.html'

    def get_context_data(self):
        context = super(HallStaffDashboardView, self).get_context_data()
        context['user'] = get_user_model().objects.prefetch_related(
            'approval_queue__author',
            'approval_queue__keywords',
            'approval_queue__recognition',
            'approval_set__experience__author',
            'approval_set__experience__keywords',
            'approval_set__experience__recognition'
        ).get(pk=self.request.user.pk)
        return context


class RAHomeView(ListView):
    access_level = 'basic'
    template_name = 'exdb/ra_home.html'
    context_object_name = 'experiences'

    def get_queryset(self):
        return Experience.objects.filter(author=self.request.user).order_by('created_datetime')

    def get_context_data(self, *args, **kwargs):
        context = super(RAHomeView, self).get_context_data(*args, **kwargs)
        context['ra'] = self.request.user

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
        week_ahead = []
        for experience in context['experience_dict'][_('Approved')]:
            if experience.start_datetime > timezone.now() and experience.start_datetime < one_week:
                week_ahead.append(experience)
        context['week_ahead'] = week_ahead
        return context


class ExperienceApprovalView(UpdateView):
    access_level = 'basic'
    template_name = 'exdb/experience_approval.html'
    form_class = ExperienceSubmitForm
    second_form_class = ApprovalForm
    model = Experience

    def get_object(self):
        return get_object_or_404(Experience, pk=self.kwargs['pk'], status='pe', next_approver=self.request.user)

    def get_success_url(self):
        return reverse('hallstaff_dash')

    def get_context_data(self, **kwargs):
        context = super(ExperienceApprovalView, self).get_context_data()
        if kwargs.get('invalid_comment'):
            context['comment_form'] = kwargs.get('invalid_comment')
        else:
            context['comment_form'] = self.second_form_class()
        context['comments'] = ExperienceComment.objects.filter(experience=context['experience'])
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        experience_form = self.get_form()
        comment_form = self.second_form_class(request.POST)
        if experience_form.is_valid() and comment_form.is_valid():
            return self.form_valid(experience_form, comment_form)
        else:
            return self.form_invalid(experience_form, comment_form)

    def form_valid(self, experience_form, comment_form):
        comment_form.instance.author = self.request.user
        experience_form.instance.author = self.get_object().author
        if self.request.POST.get('approve'):
            if experience_form.instance.next_approver == self.request.user:
                experience_form.instance.next_approver = None
                experience_form.instance.status = 'ad'
            ExperienceApproval.objects.create(experience=experience_form.instance,
                                              approver=self.request.user)
        else:
            experience_form.instance.status = 'de'
        experience_form.save()
        comment_form.instance.experience = experience_form.instance
        comment_form.save()
        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, experience_form, comment_form, **kwargs):
        if experience_form.is_valid() and self.request.POST.get('approve'):
            if experience_form.instance.next_approver == self.request.user:
                experience_form.instance.next_approver = None
                experience_form.instance.status = 'ad'
            experience_form.save()
            ExperienceApproval.objects.create(experience=experience_form.instance,
                                              approver=self.request.user)
            return HttpResponseRedirect(self.get_success_url())
        elif not experience_form.is_valid():
            return super(ExperienceApprovalView, self).form_invalid(experience_form)
        else:
            kwargs['invalid_comment'] = comment_form
            return self.render_to_response(self.get_context_data(**kwargs))


class ExperienceConclusionView(UpdateView):
    access_level = 'basic'
    template_name = 'exdb/conclusion.html'
    form_class = ExperienceConclusionForm
    model = Experience

    def get_success_url(self):
        return reverse('ra_home')

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


class EditExperienceView(UpdateView):
    access_level = 'basic'
    template_name = 'exdb/edit_experience.html'
    form_class = ExperienceSubmitForm
    model = Experience

    def get_success_url(self):
        return reverse('ra_home')

    def get_context_data(self, **kwargs):
        context = super(EditExperienceView, self).get_context_data()
        experience = get_object_or_404(Experience, pk=self.kwargs['pk'])
        context['status'] = experience.status
        context['experience_comments'] = ExperienceComment.objects.filter(experience=experience)
        return context

    def form_valid(self, form):
        if self.request.POST.get('submit'):
            form.instance.status = 'pe'
        return super(EditExperienceView, self).form_valid(form)
