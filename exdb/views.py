import csv
import json
from collections import OrderedDict
from django.views.generic import View, TemplateView, ListView, RedirectView
from django.views.generic.edit import CreateView, UpdateView
from django.shortcuts import get_object_or_404
from django.core.urlresolvers import reverse
from django.contrib import auth
from django.http import HttpResponseRedirect, Http404, HttpResponse
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth import get_user_model
from django.conf import settings
from django.db.models import Q, Prefetch

from exdb.models import Experience, ExperienceComment, ExperienceApproval, EXDBUser, Subtype, Requirement, Affiliation, Semester, Section
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
            verification = any(s.needs_verification for s in form.cleaned_data['subtypes'])
            if verification:
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

    def get_hs_queryset(self):
        experience_approvals = ExperienceApproval.objects.filter(
            approver=self.request.user, experience__status='ad'
        )
        next_approver_queue = Q(next_approver=self.request.user) & Q(status='pe')
        experiences = Experience.objects.filter(
            next_approver_queue |
            Q(pk__in=experience_approvals.values('experience'))
        )
        return experiences.distinct() | self.get_ra_queryset()

    def get_ra_queryset(self):
        return Experience.objects.filter((Q(author=self.request.user) | (Q(planners=self.request.user) &
                                                                         ~Q(status__in=('dr',)))) & ~Q(status='ca')).order_by('created_datetime').distinct()

    def get_queryset(self):
        if self.request.user.is_hallstaff():
            return self.get_hs_queryset().order_by('start_datetime')
        else:
            return self.get_ra_queryset().order_by('start_datetime')

    def get_context_data(self, *args, **kwargs):
        context = super(HomeView, self).get_context_data(*args, **kwargs)
        context['user'] = self.request.user
        experiences_shown = 3

        # This is what experience groups we are showing the user and in what order
        if self.request.user.is_hallstaff():
            status_to_display = [x[1] for x in Experience.STATUS_TYPES]
            status_to_display.insert(status_to_display.index(_('Pending Approval')), _('Needs Evaluation'))
        else:
            status_to_display = [_('Needs Evaluation')] + [x[1] for x in Experience.STATUS_TYPES]

        status_to_display.insert(status_to_display.index(_('Pending Approval')), _('Upcoming'))

        # Grouping of experiences for display
        experience_dict = OrderedDict()
        time_ahead = timezone.now()
        time_ahead += settings.HALLSTAFF_UPCOMING_TIMEDELTA if self.request.user.is_hallstaff() else settings.RA_UPCOMING_TIMEDELTA
        for status in status_to_display:
            experience_dict[status] = []
        for experience in context[self.context_object_name]:
            if experience.needs_evaluation() and len(experience_dict[_('Needs Evaluation')]) < experiences_shown:
                experience_dict[_('Needs Evaluation')].append(experience)
            else:
                if (experience.get_status_display() in experience_dict) and (
                        len(experience_dict[experience.get_status_display()]) < experiences_shown):
                    experience_dict[experience.get_status_display()].append(experience)
            if experience.status == 'ad' and experience.start_datetime > timezone.now() and experience.start_datetime < time_ahead\
                    and len(experience_dict[_('Upcoming')]) < experiences_shown and (experience not in experience_dict[_('Upcoming')]):
                experience_dict[_('Upcoming')].append(experience)
        context['experience_dict'] = experience_dict

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

    def get_form_kwargs(self, **kwargs):
        kw_args = super(ExperienceApprovalView, self).get_form_kwargs()
        kw_args['submit'] = self.request.POST.get('approve') or self.request.POST.get('deny')
        return kw_args

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
        elif self.request.POST.get('delete'):
            # If the approver decides to 'delete' the experience, skip validation
            # and do not modify any field of the experience with the exception of
            # changing the status to cancelled.
            self.object.status = 'ca'
            self.object.save()
            return HttpResponseRedirect(self.get_success_url())
        else:
            return self.form_invalid(experience_form, comment_form)

    def form_valid(self, experience_form, comment_form):
        comment_form.instance.author = self.request.user
        if self.request.POST.get('approve'):
            if experience_form.instance.next_approver == self.request.user or not experience_form.instance.next_approver:
                experience_form.instance.next_approver = None
                experience_form.instance.status = 'ad'
                experience_form.instance.needs_author_email = True
            ExperienceApproval.objects.create(experience=experience_form.instance,
                                              approver=self.request.user)
        else:
            experience_form.instance.status = 'de'
            experience_form.instance.next_approver = self.request.user
            experience_form.instance.needs_author_email = True
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
        Qs = Q(author=self.request.user) | Q(planners=self.request.user)
        if self.request.user.is_hallstaff():
            experience_approvals = ExperienceApproval.objects.filter(
                approver=self.request.user, experience__status='ad'
            )
            Qs |= Q(pk__in=experience_approvals.values('experience'))
        return Experience.objects.filter(Qs & Q(pk=self.kwargs['pk'])).distinct()

    def get_object(self, **kwargs):
        experience = super(ExperienceConclusionView, self).get_object()
        if experience.needs_evaluation():
            return experience
        raise Http404

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

    def get_success_url(self):
        return reverse('home')

    def get_form_class(self):
        if self.request.method.upper() == 'POST' and 'submit' in self.request.POST:
            return ExperienceSubmitForm
        else:
            return ExperienceSaveForm

    def get_queryset(self):
        user_has_editing_privs = Q(author=self.request.user) | (Q(planners=self.request.user) & ~Q(status='dr'))
        if self.request.user.is_hallstaff():
            # Let the staff do whatever they want to non-drafts
            user_has_editing_privs |= ~Q(status='dr')
        current_status_allows_edits = ~Q(status__in=('ca', 'co'))
        event_already_occurred = Q(status='ad') & Q(start_datetime__lte=timezone.now())
        editable_experience = user_has_editing_privs & current_status_allows_edits & ~event_already_occurred
        return Experience.objects.filter(editable_experience).prefetch_related('comment_set').distinct()

    def form_valid(self, form):
        experience = self.get_object()
        needs_reapproval = not (self.request.user.is_hallstaff() and experience.status == 'ad')
        if self.request.POST.get('submit') and needs_reapproval:
            form.instance.status = 'pe'
        if self.request.POST.get('delete') and experience.status == 'dr':
            # An experience can only be 'deleted' from this view if the status of this experience
            # in the database is draft.  Only the status is modified, no other field.
            experience.status = 'ca'
            experience.save()
            return HttpResponseRedirect(self.get_success_url())
        return super(EditExperienceView, self).form_valid(form)


class ListExperienceByStatusView(ListView):
    access_level = 'basic'
    context_object_name = 'experiences'
    template_name = 'exdb/list_experiences.html'
    readable_status = None
    status_code = ''

    def needs_eval_queryset(self):
        experience_approvals = ExperienceApproval.objects.filter(
            approver=self.request.user, experience__status='ad'
        )
        Qs = Q(end_datetime__lt=timezone.now()) & Q(status='ad')
        user_Qs = Q(author=self.request.user) | Q(planners=self.request.user)
        Qs = Qs & user_Qs
        if self.request.user.is_hallstaff():
            hallstaff_Qs = Q(
                pk__in=experience_approvals.values('experience')) & Q(
                end_datetime__lt=timezone.now(), status="ad")
            Qs = Qs | hallstaff_Qs
        return Experience.objects.filter(Qs).distinct().order_by('start_datetime')

    def upcoming_queryset(self):
        experience_approvals = ExperienceApproval.objects.filter(
            approver=self.request.user, experience__status='ad'
        )
        time_ahead = timezone.now()
        time_ahead += settings.HALLSTAFF_UPCOMING_TIMEDELTA if self.request.user.is_hallstaff() else settings.RA_UPCOMING_TIMEDELTA
        Qs = Q(status='ad') & Q(start_datetime__gt=timezone.now()) & Q(start_datetime__lt=time_ahead)
        user_Qs = (
            Q(author=self.request.user) |
            Q(planners=self.request.user) |
            Q(pk__in=experience_approvals.values('experience'))
        )
        if self.request.user.is_hallstaff():
            user_Qs = user_Qs | Q(recognition__affiliation=self.request.user.affiliation)
        Qs = Qs & user_Qs
        return Experience.objects.filter(Qs).distinct().order_by('start_datetime')

    def status_queryset(self):
        Qs = Q(author=self.request.user) | (Q(planners=self.request.user)
                                            & ~Q(status='dr')) | Q(next_approver=self.request.user, status='pe')
        Qs = Qs & Q(status=self.status)
        if self.request.user.is_hallstaff() and self.status == 'ad':
            experience_approvals = ExperienceApproval.objects.filter(
                approver=self.request.user, experience__status='ad'
            )
            Qs |= Q(pk__in=experience_approvals.values('experience'))

        return Experience.objects.filter(Qs).distinct().order_by('start_datetime')

    def get_queryset(self):
        if not self.readable_status:
            for stat in Experience.STATUS_TYPES:
                if stat[2] == self.kwargs.get('status'):
                    self.status = stat[0]
                    self.readable_status = stat[1]
                    return self.status_queryset()

        if self.readable_status == "Upcoming":
            return self.upcoming_queryset()

        if self.readable_status == "Needs Evaluation":
            return self.needs_eval_queryset()
        raise Http404('That status does not exist!')

    def get_context_data(self, *args, **kwargs):
        context = super(ListExperienceByStatusView, self).get_context_data()
        context['status'] = self.readable_status
        return context


class SearchExperienceResultsView(ListView):
    access_level = 'basic'
    context_object_name = 'experiences'
    template_name = 'exdb/search.html'
    model = Experience

    def get_queryset(self):
        tokens = self.request.GET.get('search', '').split()
        if not tokens:
            return Experience.objects.none()

        search_fields = [
            'name',
            'description',
            'goals',
            'guest',
            'guest_office',
            'conclusion',
            'keywords__name',
            'recognition__name',
            'recognition__affiliation__name',
            'planners__first_name',
            'planners__last_name',
            'author__first_name',
            'author__last_name',
            'type__name',
            'subtypes__name',
        ]

        filter_Qs = Q()
        for token in tokens:
            or_Qs = Q()
            for field in search_fields:
                or_Qs |= Q(**{field + '__icontains': token})
            filter_Qs &= or_Qs
        # This will look something like:
        # WHERE
        #     (column_1 ILIKE '%token_1%' OR column_2 ILIKE '%token_1%')
        # AND (column_1 ILIKE '%token_2%' OR column_2 ILIKE '%token_2%')
        # AND (column_1 ILIKE '%token_3%' OR column_2 ILIKE '%token_3%')
        queryset = Experience.objects.filter(filter_Qs).exclude(status='ca')

        # get rid of a users drafts for everyone else
        queryset = queryset.exclude(~Q(author=self.request.user), status='dr')

        return queryset.select_related('type').prefetch_related(
            'planners',
            'keywords',
            'recognition__affiliation',
            'subtypes',
        ).distinct()

    def get_context_data(self, *args, **kwargs):
        context = super(SearchExperienceResultsView, self).get_context_data(*args, **kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        return context


class CompletionBoardView(TemplateView):
    access_level = 'basic'
    template_name = 'exdb/completion_board.html'

    def get_context_data(self, *args, **kwargs):
        context = super(CompletionBoardView, self).get_context_data(*args, **kwargs)

        affiliation = Affiliation.objects.get(pk=self.kwargs.get('pk'))
        current_time = timezone.now()
        semester = Semester.objects.get(start_datetime__lte=current_time, end_datetime__gte=current_time)

        # Make sure this is correct
        prefetch = Prefetch(
            'experience_set',
            queryset=Experience.objects.filter(
                start_datetime__lte=semester.end_datetime,
                end_datetime__gte=semester.start_datetime,
                status='co'))

        sections = affiliation.section_set.prefetch_related(prefetch, 'experience_set__subtypes')

        for section in sections:
            section.completion_board_stuff()

        context['sections'] = sections
        context['requirements'] = sections[0].requirement_dict
        context['affiliations'] = Affiliation.objects.all()
        context['current_affiliation'] = int(self.kwargs.get('pk').strip())

        return context


class SectionCompletionBoardView(TemplateView):
    access_level = 'basic'
    template_name = 'exdb/section_completion_board.html'

    def get_context_data(self, **kwargs):
        context = super(SectionCompletionBoardView, self).get_context_data()

        section = Section.objects.get(pk=self.kwargs.get('pk'))
        section.completion_board_stuff()

        context['requirement_dict'] = section.requirement_dict
        context['section'] = section

        return context


class RequirementAdminView(TemplateView):
    access_level = 'basic'
    template_name = 'exdb/requirement_admin.html'

    def get_context_data(self, **kwargs):
        context = super(RequirementAdminView, self).get_context_data()
        context['requirements'] = Requirement.objects.all()[:20].select_related('subtype')
        context['semesters'] = Semester.objects.all()
        context['affiliations'] = Affiliation.objects.all()
        context['subtypes'] = Subtype.objects.all()
        return context


class ViewRequirementView(TemplateView):
    access_level = 'basic'
    template_name = 'exdb/requirement_view.html'

    def get_context_data(self, **kwargs):
        context = super(ViewRequirementView, self).get_context_data()
        context['requirement'] = get_object_or_404(Requirement, pk=self.kwargs['pk'])
        return context


class SearchExperienceReport(View):
    access_level = 'basic'
    keys = [
        'name', 'status', 'author', 'planners', 'recognition', 'start_datetime',
        'end_datetime', 'type', 'subtypes', 'description', 'goals', 'keywords',
        'audience', 'guest', 'guest_office', 'attendance', 'created_datetime',
        'next_approver', 'funds', 'conclusion',
    ]

    def get(self, *args, **kwargs):
        if not self.request.GET.get('experiences'):
            raise Http404
        pks = json.loads(self.request.GET.get('experiences'))
        if not pks:
            raise Http404
        experiences = Experience.objects.filter(pk__in=pks).prefetch_related(
            'planners',
            'recognition',
            'subtypes',
            'keywords',
        )
        # Filter out canceled experiences and drafts not authored by the current user.
        experiences = experiences.exclude(status='ca')
        experiences = experiences.exclude(~Q(author=self.request.user), status='dr')

        response = HttpResponse(content_type="text/csv")
        response['Content-Disposition'] = 'attachment; filename="experiences.csv"'

        writer = csv.DictWriter(response, fieldnames=self.keys)
        writer.writeheader()

        for experience in experiences:
            writer.writerow(experience.convert_to_dict(self.keys))

        return response
