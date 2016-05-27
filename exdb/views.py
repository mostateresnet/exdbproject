from collections import OrderedDict
from django.views.generic import TemplateView, ListView, RedirectView
from django.views.generic.edit import CreateView, UpdateView
from django.shortcuts import get_object_or_404
from django.core.urlresolvers import reverse
from django.contrib import auth
from django.http import HttpResponseRedirect
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth import get_user_model
from django.conf import settings
from django.db.models import Q

from exdb.models import Experience, ExperienceComment, ExperienceApproval
from .forms import ExperienceSubmitForm, ExperienceSaveForm, ApprovalForm, ExperienceConclusionForm


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


class HomeView(ListView):
    template_name = 'exdb/home.html'
    access_level = 'basic'
    context_object_name = 'experiences'

    def is_hs(self):
        return self.request.user.groups.filter(name='hs')

    def get_hs_queryset(self):
        experience_approvals = ExperienceApproval.objects.filter(
            approver=self.request.user, experience__status='ad'
        )
        experiences = Experience.objects.filter(
            Q(next_approver=self.request.user) |
            Q(pk__in=experience_approvals.values('experience'))
        )
        return experiences

    def get_ra_queryset(self):
        return Experience.objects.filter(Q(author=self.request.user) | (Q(planners=self.request.user) & ~Q(status='dr')))\
            .exclude(status__in=('ca')).order_by('created_datetime').distinct()

    def get_queryset(self):
        if self.is_hs():
            return self.get_hs_queryset()
        else:
            return self.get_ra_queryset()

    def get_context_data(self, *args, **kwargs):
        context = super(HomeView, self).get_context_data(*args, **kwargs)
        context['user'] = self.request.user

        # This is what experience groups we are showing the user and in what order
        if self.is_hs():
            status_to_display = [_('Pending Approval'), _('Approved')]
        else:
            status_to_display = [_(x[1]) for x in Experience.STATUS_TYPES]
        status_to_display.append(_('Needs Evaluation'))

        # Grouping of experiences for display
        experience_dict = OrderedDict()
        for status in status_to_display:
            experience_dict[status] = []
        approvable_experiences = self.request.user.approvable_experiences()
        for experience in context[self.context_object_name]:
            experience.can_approve = experience in approvable_experiences
            if experience.needs_evaluation():
                experience_dict[_('Needs Evaluation')].append(experience)
            else:
                if experience.get_status_display() in experience_dict:
                    experience_dict[experience.get_status_display()].append(experience)
        context['experience_dict'] = experience_dict

        # Which experiences are coming up soon enough that we want to show them
        time_ahead = timezone.now()
        time_ahead += settings.HALLSTAFF_TIME_AHEAD if self.is_hs() else settings.RA_TIME_AHEAD
        upcoming = []
        for experience in context['experience_dict'][_('Approved')]:
            if experience.start_datetime > timezone.now() and experience.start_datetime < time_ahead:
                upcoming.append(experience)
        context['upcoming'] = upcoming
        return context


class ExperienceApprovalView(UpdateView):
    access_level = 'basic'
    template_name = 'exdb/experience_approval.html'
    form_class = ExperienceSubmitForm
    second_form_class = ApprovalForm
    model = Experience

    def get_queryset(self):
        return self.request.user.approvable_experiences()

    def get_success_url(self):
        return reverse('home')

    def get_context_data(self, **kwargs):
        context = super(ExperienceApprovalView, self).get_context_data()
        if kwargs.get('invalid_comment'):
            # If the post returned form invalid and the comment form was invalid
            # this adds the comment_form with the validation errors and previous
            # input to the context data.
            context['comment_form'] = kwargs.get('invalid_comment')
        else:
            context['comment_form'] = self.second_form_class()
        context['comments'] = ExperienceComment.objects.filter(experience=context['experience'])
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        experience_form = self.get_form()
        comment_form = self.second_form_class(request.POST)
        if experience_form.is_valid() and (self.request.POST.get('approve') or comment_form.is_valid()):
            return self.form_valid(experience_form, comment_form)
        else:
            return self.form_invalid(experience_form, comment_form)

    def form_valid(self, experience_form, comment_form):
        comment_form.instance.author = self.request.user
        if self.request.POST.get('approve'):
            if experience_form.instance.next_approver == self.request.user:
                experience_form.instance.next_approver = None
                experience_form.instance.status = 'ad'
            ExperienceApproval.objects.create(experience=experience_form.instance,
                                              approver=self.request.user)
        else:
            experience_form.instance.status = 'de'
            experience_form.instance.next_approver = self.request.user
        experience_form.save()
        comment_form.instance.experience = experience_form.instance
        if comment_form.is_valid():
            comment_form.save()
        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, experience_form, comment_form, **kwargs):
        if not experience_form.is_valid():
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


class EditExperienceView(UpdateView):
    access_level = 'basic'
    template_name = 'exdb/edit_experience.html'
    form_class = ExperienceSubmitForm

    def get_success_url(self):
        return reverse('home')

    def get_queryset(self):
        user_has_editing_privs = Q(author=self.request.user) | (Q(planners=self.request.user) & ~Q(status='dr'))
        current_status_allows_edits = ~Q(status__in=('ca', 'co'))
        event_already_occurred = Q(status='ad') & Q(start_datetime__lte=timezone.now())
        editable_experience = user_has_editing_privs & current_status_allows_edits & ~event_already_occurred
        return Experience.objects.filter(editable_experience).prefetch_related('comment_set').distinct()

    def form_valid(self, form):
        if self.request.POST.get('submit'):
            form.instance.status = 'pe'
        return super(EditExperienceView, self).form_valid(form)
