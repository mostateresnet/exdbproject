from django.test import TestCase, Client, override_settings
from django.utils.timezone import datetime, timedelta, now, make_aware, utc, localtime
from django.utils.six import StringIO
from django.core.urlresolvers import reverse
from django.core import mail
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.shortcuts import get_object_or_404
from django.core.management import call_command
from django.conf import settings

from exdb.models import Affiliation, Experience, Type, SubType, Section, Keyword, ExperienceComment, ExperienceApproval, EmailTask
from exdb.forms import ExperienceSubmitForm


class StandardTestCase(TestCase):

    def setUp(self):

        self.test_date = make_aware(datetime(2015, 1, 1, 16, 1), timezone=utc)

        users = [('ra',) * 2, ('hs', 'hallstaff'), ('llc', 'hallstaff')]
        self.groups = {}

        self.clients = {}
        for user, group in users:
            self.groups[user] = Group.objects.get_or_create(name=group)[0]
            self.clients[user] = Client()
            # avoid setting the password and force_login for speed
            self.clients[user].user_object = get_user_model().objects.create(username=user)
            self.clients[user].user_object.groups.add(self.groups[user])
            self.clients[user].force_login(self.clients[user].user_object)

    def create_type(self, needs_verification=True, name="Test Type"):
        return Type.objects.get_or_create(name=name, needs_verification=needs_verification)[0]

    def create_sub_type(self, name="Test Sub Type"):
        return SubType.objects.get_or_create(name=name)[0]

    def create_affiliation(self, name="Test Affiliation"):
        return Affiliation.objects.get_or_create(name=name)[0]

    def create_section(self, name="Test Section", affiliation=None):
        a = affiliation or self.create_affiliation()
        return Section.objects.get_or_create(name=name, affiliation=a)[0]

    def create_keyword(self, name="Test Keyword"):
        return Keyword.objects.get_or_create(name=name)[0]

    def create_experience(self, exp_status, attendance=0, start=None, end=None, author=None):
        """Creates and returns an experience object with status,
        start_time, end_time and/or name of your choice"""
        start = start or self.test_date
        end = end or (self.test_date + timedelta(days=1))
        if author is None:
            author = self.clients['ra'].user_object
        return Experience.objects.get_or_create(
            author=author,
            name="Test Experience",
            description="test description",
            start_datetime=start,
            end_datetime=end,
            type=self.create_type(),
            sub_type=self.create_sub_type(),
            goal="Test Goal",
            audience="b",
            status=exp_status,
            attendance=attendance,
            next_approver=self.clients['hs'].user_object,
        )[0]

    def create_experience_comment(self, exp, message="Test message"):
        """Creates experience comment, must pass an experience"""
        return ExperienceComment.objects.get_or_create(
            experience=exp,
            message=message,
            author=self.clients['ra'].user_object,
            timestamp=self.test_date
        )[0]


class ModelCoverageTest(StandardTestCase):

    def test_sub_type_str_method(self):
        st = self.create_sub_type()
        self.assertEqual(str(SubType.objects.get(pk=st.pk)), st.name,
                         u"SubType object should have been created.")

    def test_type_str_method(self):
        t = self.create_type()
        self.assertEqual(str(Type.objects.get(pk=t.pk)), t.name, "Type object should have been created.")

    def test_section_str_method(self):
        o = self.create_section()
        self.assertEqual(str(Section.objects.get(pk=o.pk)), o.name,
                         "Section object should have been created.")

    def test_keyword_str_method(self):
        k = self.create_keyword()
        self.assertEqual(str(Keyword.objects.get(pk=k.pk)), k.name, "Keyword object should have been created.")

    def test_experience_str_method(self):
        e = self.create_experience('dr')
        self.assertEqual(str(Experience.objects.get(pk=e.pk)), e.name, "Experience object should have been created.")

    def test_affiliation_str_method(self):
        a = self.create_affiliation()
        self.assertEqual(str(Affiliation.objects.get(pk=a.pk)), a.name, "Affiliation object should have been created.")

    def test_experience_comment_message(self):
        ec = self.create_experience_comment(self.create_experience('de'))
        self.assertEqual(ExperienceComment.objects.get(pk=ec.pk).message, ec.message,
                         "ExperienceComment object should have been created.")

    def test_experience_needs_evaluation(self):
        e = self.create_experience('ad')
        self.assertTrue(e.needs_evaluation(), "This experience should return true for needs evaluation.")

    def test_get_url_returns_conclusion(self):
        e = self.create_experience('ad', start=(now() - timedelta(days=2)), end=(now() - timedelta(days=1)))
        self.assertEqual(e.get_url(self.clients['ra'].user_object), reverse('conclusion', args=[e.pk]),
                         "The url for experience conclusion should have been returned")

    def test_get_url_returns_approval(self):
        e = self.create_experience('pe')
        self.assertEqual(e.get_url(self.clients['hs'].user_object), reverse('approval', args=[e.pk]),
                         "The url for experience approval should have been returned")

    def test_get_url_returns_view_experience(self):
        e = self.create_experience('co')
        self.assertEqual(e.get_url(self.clients['ra'].user_object), reverse('view_experience', args=[e.pk]),
                         "The url for view_experience should have been returned")

    def test_get_url_returns_edit(self):
        e = self.create_experience('pe', start=(now() + timedelta(days=2)), end=(now() + timedelta(days=3)))
        self.assertEqual(e.get_url(self.clients['ra'].user_object), reverse('edit', args=[e.pk]),
                         "The url for experience edit should have been returned")


class ExperienceCreationFormTest(StandardTestCase):

    def setUp(self):
        StandardTestCase.setUp(self)
        self.test_type = self.create_type()
        self.test_past_type = self.create_type(needs_verification=False)
        self.test_sub_type = self.create_sub_type()
        self.test_org = self.create_section()
        self.test_keyword = self.create_keyword()

    def get_post_data(self, start, end):
        return {'start_datetime': start,
                'end_datetime': end,
                'name': 'test',
                'description': 'test',
                'type': self.test_type.pk,
                'sub_type': self.test_sub_type.pk,
                'audience': 'c',
                'guest': 'test',
                'recognition': [self.test_org.pk],
                'keywords': [self.test_keyword.pk],
                'goal': 'test',
                'next_approver': self.clients['hs'].user_object.pk}

    def test_valid_experience_creation_form(self):
        data = self.get_post_data((self.test_date + timedelta(days=1)), (self.test_date + timedelta(days=2)))
        form = ExperienceSubmitForm(data, when=self.test_date)
        self.assertTrue(form.is_valid(), "Form should have been valid")

    def test_valid_past_experience_creation(self):
        data = self.get_post_data((self.test_date - timedelta(days=2)), (self.test_date - timedelta(days=1)))
        data['attendance'] = 1
        data['type'] = self.test_past_type.pk
        data['conclusion'] = "Test conclusion"
        form = ExperienceSubmitForm(data, when=self.test_date)
        self.assertTrue(form.is_valid(), "Form should have been valid")

    def test_past_experience_without_audience(self):
        data = self.get_post_data((self.test_date - timedelta(days=2)), (self.test_date - timedelta(days=1)))
        data.pop('audience', None)
        data['attendance'] = 1
        data['type'] = self.test_past_type.pk
        form = ExperienceSubmitForm(data, when=self.test_date)
        self.assertFalse(form.is_valid(), "Form should NOT have been valid")

    def test_past_experience_type_with_future_dates(self):
        data = self.get_post_data((self.test_date + timedelta(days=1)), (self.test_date + timedelta(days=2)))
        data['attendance'] = 1
        data['type'] = self.test_past_type.pk
        form = ExperienceSubmitForm(data, when=self.test_date)
        self.assertFalse(form.is_valid(), "Form should NOT have been valid")

    def test_future_experience_type_with_past_dates(self):
        data = self.get_post_data((self.test_date - timedelta(days=2)), (self.test_date - timedelta(days=1)))
        form = ExperienceSubmitForm(data, when=self.test_date)
        self.assertFalse(form.is_valid(), "Form should NOT have been valid")

    def test_future_experience_with_start_date_after_end_date(self):
        data = self.get_post_data((self.test_date + timedelta(days=3)), (self.test_date + timedelta(days=2)))
        form = ExperienceSubmitForm(data, when=self.test_date)
        self.assertFalse(form.is_valid(), "Form should NOT have been valid")

    def test_past_experience_creation_no_attendance(self):
        data = self.get_post_data((self.test_date - timedelta(days=2)), (self.test_date - timedelta(days=1)))
        data['type'] = self.test_past_type.pk
        form = ExperienceSubmitForm(data, when=self.test_date)
        self.assertFalse(form.is_valid(), "Form should NOT have been valid")

    def test_experience_creation_with_attendance(self):
        data = self.get_post_data((self.test_date + timedelta(days=1)), (self.test_date + timedelta(days=2)))
        data['attendance'] = 1
        form = ExperienceSubmitForm(data, when=self.test_date)
        self.assertFalse(form.is_valid(), "Form should NOT have been valid")

    def test_past_experience_creation_negative_attendance(self):
        data = self.get_post_data((self.test_date - timedelta(days=2)), (self.test_date - timedelta(days=1)))
        data['attendance'] = -1
        data['type'] = self.test_past_type.pk
        form = ExperienceSubmitForm(data, when=self.test_date)
        self.assertFalse(form.is_valid(), "Form should NOT have been valid")

    def test_experience_creation_form_no_end_date(self):
        data = self.get_post_data((self.test_date + timedelta(days=1)), (self.test_date + timedelta(days=1)))
        data.pop('end_datetime', None)
        form = ExperienceSubmitForm(data, when=self.test_date)
        self.assertFalse(form.is_valid(), "Form should NOT have been valid")

    def test_experience_creation_form_no_start_date(self):
        data = self.get_post_data((self.test_date + timedelta(days=1)), (self.test_date + timedelta(days=1)))
        data.pop('start_datetime', None)
        form = ExperienceSubmitForm(data, when=self.test_date)
        self.assertFalse(form.is_valid(), "Form should NOT have been valid")

    def test_experience_creation_form_no_sub_type(self):
        data = self.get_post_data((self.test_date + timedelta(days=1)), (self.test_date + timedelta(days=2)))
        data.pop('sub_type', None)
        form = ExperienceSubmitForm(data, when=self.test_date)
        self.assertFalse(form.is_valid(), "Form should NOT have been valid")

    def test_experience_creation_form_no_type(self):
        data = self.get_post_data((self.test_date + timedelta(days=1)), (self.test_date + timedelta(days=2)))
        data.pop('type', None)
        form = ExperienceSubmitForm(data, when=self.test_date)
        self.assertFalse(form.is_valid(), "Form should NOT have been valid")

    def test_experience_creation_no_supervisor(self):
        data = self.get_post_data((self.test_date + timedelta(days=1)), (self.test_date + timedelta(days=2)))
        data['next_approver'] = None
        form = ExperienceSubmitForm(data, when=self.test_date)
        self.assertFalse(form.is_valid(), "Form should NOT have been valid if next_approver is not specified")

    def test_experience_creation_spontaneous_no_conclusion(self):
        data = self.get_post_data((self.test_date - timedelta(days=2)), (self.test_date - timedelta(days=1)))
        data['attendance'] = 1
        data['type'] = self.test_past_type.pk
        data['conclusion'] = ""
        form = ExperienceSubmitForm(data, when=self.test_date)
        self.assertFalse(form.is_valid(), "Form should not be valid with no conclusion if it does not need approval")

    def test_experience_creation_invalid_supervisor(self):
        data = self.get_post_data((self.test_date + timedelta(days=1)), (self.test_date + timedelta(days=2)))
        data['next_approver'] = self.clients['ra'].user_object.pk
        form = ExperienceSubmitForm(data, when=self.test_date)
        self.assertFalse(form.is_valid(), "Form should not be valid if next_approver is not hallstaff")


class ExperienceCreationViewTest(StandardTestCase):

    def setUp(self):
        StandardTestCase.setUp(self)
        self.test_type = self.create_type()
        self.test_past_type = self.create_type(needs_verification=False)
        self.test_sub_type = self.create_sub_type()
        self.test_org = self.create_section()
        self.test_keyword = self.create_keyword()

    def get_post_data(self, start, end, action='submit'):
        return {'start_datetime': start.strftime("%Y-%m-%d %H:%M:%S"),
                'end_datetime': end.strftime("%Y-%m-%d %H:%M"),
                'name': 'test',
                'description': 'test',
                'type': self.test_type.pk,
                'sub_type': self.test_sub_type.pk,
                'audience': 'c',
                'guest': 'test',
                'recognition': [self.test_org.pk],
                'keywords': [self.test_keyword.pk],
                'next_approver': self.clients['hs'].user_object.pk,
                'goal': 'test',
                action: action}

    def test_gets_create(self):
        response = self.clients['ra'].get(reverse('create_experience'))
        self.assertEqual(response.status_code, 200, "The create experience page should have loaded")

    def test_valid_future_experience_creation_view_submit(self):
        start = now() + timedelta(days=1)
        end = now() + timedelta(days=2)
        data = self.get_post_data(start, end)
        self.clients['ra'].post(reverse('create_experience'), data)
        self.assertEqual('pe', Experience.objects.get(name='test').status,
                         "Experience should have been saved with pending status")

    def test_valid_experience_creation_view_save(self):
        start = now() + timedelta(days=1)
        end = now() + timedelta(days=2)
        data = self.get_post_data(start, end, action='save')
        self.clients['ra'].post(reverse('create_experience'), data)
        self.assertEqual('dr', Experience.objects.get(name='test').status,
                         "Experience should have been saved with draft status")

    def test_valid_past_experience_creation_view_submit(self):
        start = now() - timedelta(days=2)
        end = now() - timedelta(days=1)
        data = self.get_post_data(start, end)
        data['attendance'] = 1
        data['type'] = self.test_past_type.pk
        data['conclusion'] = "Test conclusion"
        self.clients['ra'].post(reverse('create_experience'), data)
        self.assertEqual('co', Experience.objects.get(name='test').status,
                         "Experience should have been saved with completed status")

    def test_conclusion_set_to_empty_string_if_needs_verification(self):
        start = now() + timedelta(days=1)
        end = now() + timedelta(days=2)
        data = self.get_post_data(start, end)
        data['conclusion'] = "Test Conclusion"
        self.clients['ra'].post(reverse('create_experience'), data)
        self.assertEqual(Experience.objects.get(name='test').conclusion, "",
                         "The conclusion should have been set to the empty string")


class ViewExperienceViewTest(StandardTestCase):

    def test_gets_experience(self):
        e = self.create_experience('pe')
        response = self.clients['ra'].get(reverse('view_experience', kwargs={'pk': str(e.pk)}))
        self.assertEqual(response.context['experience'].pk, e.pk, "The correct experience was not retrieved.")


class ExperienceConclusionViewTest(StandardTestCase):

    def post_data(self, attendance=1, conclusion="Test Conclusion"):
        """posts data with optional attendance and conclusion args,
        returns experience for query/comparison purposes"""
        e = self.create_experience('ad')
        self.clients['ra'].post(reverse('conclusion', kwargs={'pk': str(e.pk)}),
                                {'attendance': attendance, 'conclusion': conclusion})
        e = Experience.objects.get(pk=e.pk)
        return e

    def test_conclusion_success(self):
        e = self.post_data()
        self.assertEqual(e.status, 'co', "The experience status should be changed to completed ('co')")

    def test_no_attendance(self):
        e = self.post_data(attendance=0)
        self.assertEqual(e.status, 'ad', "The experience should not be complete without an attendance.")

    def test_negative_attendance(self):
        e = self.post_data(attendance=-1)
        self.assertEqual(e.status, 'ad', "The experience should not accept a negative attendance.")

    def test_no_conclusion(self):
        e = self.post_data(conclusion="")
        self.assertEqual(e.status, 'ad', "The experience should not be complete without a conclusion.")


class RAHomeViewTest(StandardTestCase):

    def test_coverage(self):
        self.create_experience('pe')
        self.create_experience('dr')
        response = self.clients['ra'].get(reverse('home'))

        self.assertEqual(len(response.context["experiences"]), 2, "There should be 2 experiences displayed")

    def test_does_not_get_cancelled(self):
        self.create_experience('ca')
        response = self.clients['ra'].get(reverse('home'))
        self.assertEqual(len(response.context['experiences']), 0,
                         "Cancelled experiences should not appear on any home page")

    def test_gets_drafts_when_author(self):
        e = self.create_experience('dr', author=self.clients['ra'].user_object)
        response = self.clients['ra'].get(reverse('home'))
        self.assertIn(e, response.context['experiences'],
                      'The home page should list drafts where a user is the author')

    def test_does_not_get_drafts_when_not_author(self):
        e = self.create_experience('dr', author=self.clients['hs'].user_object)
        e.planners.add(self.clients['ra'].user_object)
        response = self.clients['ra'].get(reverse('home'))
        self.assertNotIn(e, response.context['experiences'],
                         'The home page should not list drafts where a user is a planner but not an author')

    @override_settings(HALLSTAFF_UPCOMING_TIMEDELTA=timedelta(days=0), RA_UPCOMING_TIMEDELTA=timedelta(days=31))
    def test_week_ahead(self):
        self.create_experience('ad')
        Experience.objects.get_or_create(author=self.clients['ra'].user_object,
                                         name="E1", description="test description",
                                         start_datetime=(now() + timedelta(days=2)),
                                         end_datetime=(now() + timedelta(days=3)),
                                         type=self.create_type(),
                                         sub_type=self.create_sub_type(),
                                         goal="Test Goal",
                                         audience="b",
                                         status="ad",
                                         attendance=3)
        response = self.clients['ra'].get(reverse('home'))
        self.assertEqual(len(response.context["experience_dict"]["Upcoming"]),
                         1, "There should be 1 experience in the next month")


class ExperienceApprovalViewTest(StandardTestCase):

    def post_data(self, message="", submit="deny", invalid_description=False, llc_approval=False):
        """Posts approval/denial data and returns updated experience for comparisons
        default value is no comment and deny"""
        e = self.create_experience('pe', start=(now() + timedelta(days=1)), end=(now() + timedelta(days=2)))
        description = "" if invalid_description else e.description
        next_approver = self.clients['llc'].user_object.pk if llc_approval else ""
        self.clients['hs'].post(reverse('approval', args=[e.pk]), {
            'name': e.name,
            'description': description,
            'start_datetime': e.start_datetime.strftime("%Y-%m-%d %H:%M:%S"),
            'end_datetime': e.end_datetime.strftime("%Y-%m-%d %H:%M:%S"),
            'type': e.type.pk,
            'sub_type': e.sub_type.pk,
            'audience': e.audience,
            'attendance': 0,
            'goal': e.goal,
            'guest': e.guest,
            'guest_office': e.guest_office,
            'message': message,
            'next_approver': next_approver,
            submit: submit})
        return get_object_or_404(Experience, pk=e.pk)

    def test_gets_correct_experience(self):
        e = self.create_experience('pe')
        self.create_experience('pe')
        response = self.clients['hs'].get(reverse('approval', args=[e.pk]))
        self.assertEqual(response.context['experience'].pk, e.pk, "The correct experience was not retrieved.")

    def test_404_when_experience_not_pending(self):
        e = self.create_experience('dr')
        response = self.clients['hs'].get(reverse('approval', args=[e.pk]))
        self.assertEqual(
            response.status_code,
            404,
            "Attempting to retrieve a non-pending experience did not generate a 404.")

    def test_does_not_allow_deny_without_comment(self):
        e = self.post_data()
        self.assertEqual(e.status, 'pe', "An experience cannot be denied without a comment.")

    def test_approves_experience_no_comment(self):
        e = self.post_data(submit="approve")
        self.assertEqual(e.status, 'ad', "Approval should be allowed without a comment")

    def test_approves_experience_with_comment(self):
        e = self.post_data(message="Test Comment", submit="approve")
        self.assertEqual(e.status, 'ad', "Approval should be allowed with a comment")

    def test_does_not_allow_invalid_experience_edit(self):
        e = self.post_data(submit="approve", invalid_description=True)
        self.assertEqual(e.status, 'pe', "Approve/Deny should not be allowed if there is an invalid edit.")

    def test_creates_comment(self):
        e = self.post_data(message="Test Message")
        comments = ExperienceComment.objects.filter(experience=e)
        self.assertEqual(len(comments), 1, "A comment should have been created.")

    def test_does_not_create_comment(self):
        e = self.post_data()
        comments = ExperienceComment.objects.filter(experience=e)
        self.assertEqual(
            len(comments),
            0,
            "If message is an empty string, no ExperienceComment object should be created.")

    def test_does_not_change_status_if_sent_to_llc_approver(self):
        e = self.post_data(llc_approval=True, submit="approve")
        self.assertEqual(e.status, 'pe', "If sent to LLC approver, status should still be pending")

    def test_sets_next_approver_to_user_if_denied(self):
        e = self.post_data(llc_approval=True)
        self.assertEqual(
            e.next_approver,
            self.clients['hs'].user_object,
            "If denied, next approver should be denying user.")

    def test_delete_experience(self):
        e = self.post_data(submit="delete")
        self.assertEqual(e.status, 'ca', "The status should have been changed to cancelled")


class HallStaffDashboardViewTest(StandardTestCase):

    def test_get_user(self):
        self.create_experience('pe')
        self.create_experience('dr')
        response = self.clients['ra'].get(reverse('home'))

        self.assertEqual(
            response.context["user"].pk,
            self.clients['ra'].user_object.pk,
            "The correct user was not retrieved!"
        )

    def test_number_of_experiences(self):
        self.create_experience('pe')
        self.create_experience('dr')
        response = self.clients['ra'].get(reverse('home'))

        self.assertEqual(len(response.context["experiences"]), 2, "There should be 2 experiences displayed")

    def test_does_not_get_drafts_when_hs_not_author(self):
        self.create_experience('dr')
        response = self.clients['hs'].get(reverse('home'))
        self.assertEqual(len(response.context['experiences']), 0,
                         "Hallstaff should not see drafts if they are not the author")

    def test_gets_drafts_when_hs_is_author(self):
        self.create_experience('dr', author=self.clients['hs'].user_object)
        response = self.clients['hs'].get(reverse('home'))
        self.assertEqual(len(response.context['experiences']), 1,
                         "Hallstaff should be able to see their own drafts")

    @override_settings(HALLSTAFF_UPCOMING_TIMEDELTA=timedelta(days=7), RA_UPCOMING_TIMEDELTA=timedelta(days=0))
    def test_week_ahead(self):
        e1 = self.create_experience('ad')
        e2 = Experience.objects.get_or_create(author=self.clients['ra'].user_object,
                                              name="E1", description="test description",
                                              start_datetime=(now() + timedelta(days=2)),
                                              end_datetime=(now() + timedelta(days=3)),
                                              type=self.create_type(),
                                              sub_type=self.create_sub_type(),
                                              goal="Test Goal",
                                              audience="b",
                                              status="ad",
                                              attendance=None,
                                              next_approver=self.clients['hs'].user_object)[0]
        ExperienceApproval.objects.create(experience=e1, approver=self.clients['hs'].user_object)
        ExperienceApproval.objects.create(experience=e2, approver=self.clients['hs'].user_object)
        response = self.clients['hs'].get(reverse('home'))
        self.assertEqual(len(response.context["experience_dict"]["Upcoming"]),
                         1, "There should be 1 experience in the next week")


class EditExperienceViewTest(StandardTestCase):

    def post_data(self, status='pe', invalid_description=False, save=False, author=None, client=None, delete=False):
        e = self.create_experience(status, start=(now() + timedelta(days=1)),
                                   end=(now() + timedelta(days=2)), author=author)
        if status == 'ad' or (status in ('dr', 'de') and not save and not delete):
            submit = 'submit'
        elif delete:
            submit = 'delete'
        else:
            submit = 'save'
        description = "" if invalid_description else e.description
        if client is None:
            client = self.clients['ra']
        client.post(reverse('edit', args=[e.pk]), {
            'name': e.name,
            'description': description,
            'start_datetime': e.start_datetime.strftime("%Y-%m-%d %H:%M:%S"),
            'end_datetime': e.end_datetime.strftime("%Y-%m-%d %H:%M:%S"),
            'type': e.type.pk,
            'sub_type': e.sub_type.pk,
            'audience': e.audience,
            'attendance': 0,
            'goal': e.goal,
            'guest': e.guest,
            'guest_office': e.guest_office,
            'next_approver': self.clients['hs'].user_object.pk,
            submit: submit})
        return get_object_or_404(Experience, pk=e.pk)

    def test_resubmit_edited_approved_experience(self):
        e = self.post_data(status='ad')
        self.assertEqual(e.status, 'pe', "An edited approved experience should be re-submitted.")

    def test_resubmit_denied_experience(self):
        e = self.post_data(status='de')
        self.assertEqual(e.status, 'pe', "A re-submitted denied experience status should be pending.")

    def test_submits_submitted_draft(self):
        e = self.post_data(status='dr')
        self.assertEqual(e.status, 'pe', "A submitted draft should gain pending status.")

    def test_does_not_change_edited_pending_status(self):
        e = self.post_data()
        self.assertEqual(e.status, 'pe', "An edited pending experience should not have its status changed.")

    def test_does_not_change_draft_status_when_saved(self):
        e = self.post_data('dr', save=True)
        self.assertEqual(e.status, 'dr', "A saved draft should have no status change.")

    def test_saved_denied_experience_no_status_change(self):
        e = self.post_data('de', save=True)
        self.assertEqual(e.status, 'de', "A saved denied experience should have no status change.")

    def test_does_not_submit_invalid(self):
        e = self.post_data('ad', invalid_description=True)
        self.assertEqual(e.status, 'ad', "An invalid experience should not be submitted.")

    def test_delete_draft(self):
        e = self.post_data('dr', delete=True)
        self.assertEqual(e.status, 'ca', "A draft should be allowed to be cancelled")

    def test_does_not_delete_non_draft(self):
        e = self.post_data('pe', delete=True)
        self.assertEqual(e.status, 'pe', "Only drafts may be cancelled from the edit page")

    def test_hallstaff_allowed_to_edit_non_drafts(self):
        e = self.create_experience('ad', start=(now() + timedelta(days=1)), end=(now() + timedelta(days=2)))
        response = self.clients['hs'].get(reverse('edit', args=[e.pk]))
        self.assertEqual(
            response.status_code,
            200,
            'Hall Staff users SHOULD be allowed to edit approved experiences made by others')

    def test_hallstaff_not_allowed_to_edit_drafts(self):
        e = self.create_experience('dr', start=(now() + timedelta(days=1)), end=(now() + timedelta(days=2)))
        response = self.clients['hs'].get(reverse('edit', args=[e.pk]))
        self.assertEqual(
            response.status_code,
            404,
            'Hall Staff users should NOT be allowed to edit approved experiences made by others')

    def test_hallstaff_allowed_to_edit_own_drafts(self):
        e = self.create_experience('dr',
                                   start=(now() + timedelta(days=1)),
                                   end=(now() + timedelta(days=2)),
                                   author=self.clients['hs'].user_object)
        response = self.clients['hs'].get(reverse('edit', args=[e.pk]))
        self.assertEqual(
            response.status_code,
            200,
            'Hall Staff users SHOULD be allowed to edit their own "draft" experiences')

    def test_hallstaff_edit_approved_experience_stays_approved(self):
        e = self.post_data(status='ad', client=self.clients['hs'])
        self.assertEqual(e.status, 'ad', "A hallstaff-edited approved experience should remain approved")


class LoginViewTest(StandardTestCase):
    credentials = ('username', 'a@a.com', 'password')

    @classmethod
    def setUpClass(cls):
        super(LoginViewTest, cls).setUpClass()
        get_user_model().objects.create_user(*cls.credentials)

    def test_login_success(self):
        username, _, password = self.credentials
        response = Client().post(reverse('login'), {'username': username, 'password': password})
        self.assertRedirects(response, reverse('home'))

    def test_login_failure(self):
        username, _, password = self.credentials
        c = Client()
        c.post(reverse('login'), {'username': username, 'password': password + 'wrong'})
        self.assertNotIn('_auth_user_id', c.session)

    def test_unauthorized_access_redirects_login(self):
        response = Client().get(reverse('home'))
        self.assertEqual(response.url.split('?')[0], reverse('login'))


@override_settings(TIME_ZONE='UTC')
class EmailTest(StandardTestCase):

    def setUp(self):
        super(EmailTest, self).setUp()
        # Redefine now() so is_time_to_send in emails will return true and
        # we will be able to test the send function.
        from exdb import emails
        self.orig_now = emails.now
        emails.now = lambda: self.test_date

    def tearDown(self):
        from exdb import emails
        emails.now = self.orig_now

    def send_emails(self):
        out = StringIO()
        call_command('email', '--create', stdout=out)
        call_command('email', '--send', stdout=out)

    def test_sends_correct_number_of_emails(self):
        self.create_experience('pe', start=(self.test_date - timedelta(days=2)),
                               end=(self.test_date - timedelta(days=1)))
        self.create_experience('ad', start=(self.test_date + timedelta(days=2)),
                               end=(self.test_date + timedelta(days=3)))

        self.send_emails()

        self.assertEqual(len(mail.outbox), 1, "Only one email should have been sent")

    def test_sends_needs_evaluation(self):
        e = self.create_experience('ad', start=(self.test_date - timedelta(days=3)),
                                   end=(self.test_date - timedelta(days=2)))
        ExperienceApproval.objects.get_or_create(experience=e, approver=e.next_approver)
        self.create_experience('pe', start=(self.test_date - timedelta(days=2)),
                               end=(self.test_date - timedelta(days=1)))

        self.send_emails()

        self.assertEqual(len(mail.outbox), 2, "Two emails should be sent")

    def test_does_not_send_if_no_applicable_email(self):
        self.create_experience('co', start=(self.test_date - timedelta(days=2)),
                               end=(self.test_date - timedelta(days=1)))
        e = self.create_experience('ad', start=(self.test_date + timedelta(days=3)),
                                   end=(self.test_date + timedelta(days=4)))
        ExperienceApproval.objects.get_or_create(experience=e, approver=e.next_approver)

        self.send_emails()

        self.assertEqual(len(mail.outbox), 0, "0 emails should be sent")

    def test_sends_update_email(self):
        e = self.create_experience('ad', start=(self.test_date + timedelta(days=2)),
                                   end=(self.test_date + timedelta(days=3)))
        e.needs_author_email = True
        e.save()

        self.send_emails()

        self.assertEqual(len(mail.outbox), 1, "1 email should be sent")

    def test_does_not_send_daily_not_1600(self):
        from exdb import emails
        emails.now = lambda: make_aware(datetime(2015, 1, 1, 15, 1), timezone=utc)

        self.create_experience('pe', start=(self.test_date - timedelta(days=2)),
                               end=(self.test_date - timedelta(days=1)))

        self.send_emails()

        self.assertEqual(len(mail.outbox), 0, "0 emails should have been sent")

    def test_needs_author_email_is_updated(self):
        e = self.create_experience('de', start=(self.test_date + timedelta(days=3)),
                                   end=(self.test_date + timedelta(days=4)))
        e.needs_author_email = True
        e.save()

        self.send_emails()

        self.assertEqual(len(mail.outbox), 1, 'The denial email should have been sent')

        e = Experience.objects.get(pk=e.pk)
        self.assertFalse(
            e.needs_author_email,
            'needs_author_email should have been reset to False after sending the email')

    def test_last_evaluation_email_datetime_is_updated(self):
        e = self.create_experience('ad', start=(self.test_date - timedelta(days=3)),
                                   end=(self.test_date - timedelta(days=2)))

        self.send_emails()

        self.assertEqual(len(mail.outbox), 1, 'The evaluation reminder email should have been sent')
        e = Experience.objects.get(pk=e.pk)
        self.assertEqual(e.last_evaluation_email_datetime, self.test_date,
                         'last_evaluation_email_datetime should be set to now()')

    def test_emailtask_str_method(self):
        name = 'asdf'
        et = EmailTask(name=name)
        self.assertEqual(str(et), name)

    def test_email_continuity_after_error_experience_status_update(self):
        from exdb import emails
        mass_mail = emails.send_mass_mail

        e = self.create_experience('ad', start=(self.test_date - timedelta(days=3)),
                                   end=(self.test_date - timedelta(days=2)))
        e.needs_author_email = True

        with self.assertRaises(TypeError):
            emails.send_mass_mail = 1
            self.send_emails()

        self.assertFalse(Experience.objects.get(pk=e.pk).needs_author_email)

        emails.send_mass_mail = mass_mail

    def test_email_continuity_after_error_evaluate_experience(self):
        from exdb import emails
        mass_mail = emails.send_mass_mail

        e = self.create_experience('ad', start=(self.test_date - timedelta(days=3)),
                                   end=(self.test_date - timedelta(days=2)))

        with self.assertRaises(TypeError):
            emails.send_mass_mail = 1
            self.send_emails()

        self.assertIsNone(Experience.objects.get(pk=e.pk).last_evaluation_email_datetime)

        emails.send_mass_mail = mass_mail


class LogoutTest(StandardTestCase):

    def test_logout(self):
        response = self.clients['ra'].get(reverse('logout'))
        self.assertFalse(response.wsgi_request.user.is_authenticated(), "User should have been logged out")


class ListExperienceByStatusViewTest(StandardTestCase):

    def setUp(self):
        super(ListExperienceByStatusViewTest, self).setUp()
        self.hs_timedelta = settings.HALLSTAFF_UPCOMING_TIMEDELTA
        self.ra_timedelta = settings.RA_UPCOMING_TIMEDELTA

    def test_status_list_view(self):
        e = self.create_experience('pe')
        ad = self.create_experience('ad')
        url_arg = ''
        for status in Experience.STATUS_TYPES:
            if status[0] == e.status:
                url_arg = status[2]
        response = self.clients['ra'].get(reverse('status_list', kwargs={'status': url_arg}))
        self.assertIn(e, response.context['experiences'], "The view should have returned the pending experience")
        self.assertNotIn(
            ad,
            response.context['experiences'],
            "The view should have only returned one status of experiences")

    def test_upcoming_list_view(self):
        upcoming_e = self.create_experience('ad', start=(now() + self.ra_timedelta - timedelta(days=2)),
                                            end=(now() + self.ra_timedelta - timedelta(days=1)))
        future_e = self.create_experience('ad', start=(now() + self.ra_timedelta + timedelta(days=1)),
                                          end=(now() + self.ra_timedelta + timedelta(days=2)))
        response = self.clients['ra'].get(reverse('upcoming_list'))
        self.assertIn(
            upcoming_e,
            response.context['experiences'],
            'This view should have returned the experience coming up in the next week')
        self.assertNotIn(
            future_e,
            response.context['experiences'],
            'This view should not have returned experiences too far in the future')

    def test_needs_evaluation_list_view(self):
        needs_eval_e = self.create_experience('ad', start=(now() - timedelta(days=2)), end=(now() - timedelta(days=1)))
        future_e = self.create_experience('ad', start=(now() + timedelta(days=1)), end=(now() + timedelta(days=2)))
        response = self.clients['ra'].get(reverse('eval_list'))
        self.assertIn(needs_eval_e, response.context['experiences'],
                      'This view should have returned the experience that needs evaluation')
        self.assertNotIn(future_e, response.context['experiences'],
                         'This view should not return experiences that have yet to start')

    def test_upcoming_list_hs_view(self):
        hs_author_e = self.create_experience(
            'ad',
            start=(now() + self.hs_timedelta - timedelta(days=2)),
            end=(now() + self.hs_timedelta - timedelta(days=1)),
            author=self.clients['hs'].user_object
        )
        hs_author_future_e = self.create_experience(
            'ad',
            start=(now() + self.hs_timedelta + timedelta(days=1)),
            end=(now() + self.hs_timedelta + timedelta(days=2)),
            author=self.clients['hs'].user_object
        )
        upcoming_affiliation_e = self.create_experience(
            'ad',
            start=(now() + self.hs_timedelta - timedelta(days=2)),
            end=(now() + self.hs_timedelta - timedelta(days=1))
        )

        a = self.create_affiliation()
        s = self.create_section(affiliation=a)
        self.clients['hs'].user_object.affiliation = a
        self.clients['hs'].user_object.save()
        upcoming_affiliation_e.recognition.add(s)

        response = self.clients['hs'].get(reverse('upcoming_list'))
        self.assertIn(hs_author_e, response.context['experiences'],
                      'This view should have returned the upcoming experience where hs user was the author')
        self.assertIn(upcoming_affiliation_e, response.context['experiences'],
                      'The view should have returned upcoming experiences with hs user affiliation')
        self.assertNotIn(hs_author_future_e, response.context['experiences'],
                         'The view should not have returned experiences that start too far in the future')

    def test_needs_evaluation_list_hs_view(self):
        needs_eval_e = self.create_experience('ad', start=(now() - timedelta(days=2)), end=(now() - timedelta(days=1)))
        ExperienceApproval.objects.create(experience=needs_eval_e, approver=self.clients['hs'].user_object)
        response = self.clients['hs'].get(reverse('eval_list'))
        self.assertIn(needs_eval_e, response.context['experiences'],
                      'The view should have returned experiences needing evaluation that were approved by the hs user')

    def test_gets_404_when_passed_nonsensical_status(self):
        response = self.clients['ra'].get(reverse('status_list', kwargs={'status': 'aaaaaaaa'}))
        self.assertEqual(response.status_code, 404, 'The view should have responded to nonsense with a 404')
