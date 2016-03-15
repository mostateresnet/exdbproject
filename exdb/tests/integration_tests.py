from django.test import TestCase, Client
from django.utils.timezone import datetime, timedelta, now, make_aware, utc
from django.core.urlresolvers import reverse
from django.contrib.auth import get_user_model

from exdb.models import Experience, Type, SubType, Organization, Keyword, ExperienceComment
from exdb.forms import ExperienceSubmitForm


class StandardTestCase(TestCase):

    def setUp(self):
        self.test_date = make_aware(datetime(2015, 1, 1, 1, 30), timezone=utc)
        users = ['ra', 'hs']
        self.clients = {}
        for user in users:
            self.clients[user] = Client()
            # avoid setting the password and force_login for speed
            self.clients[user].user_object = get_user_model().objects.create(username=user)
            self.clients[user].force_login(self.clients[user].user_object)

    def create_type(self, needs_verification=True, name="Test Type"):
        return Type.objects.get_or_create(name=name, needs_verification=needs_verification)[0]

    def create_sub_type(self, name="Test Sub Type"):
        return SubType.objects.get_or_create(name=name)[0]

    def create_org(self, name="Test Organization"):
        return Organization.objects.get_or_create(name=name)[0]

    def create_keyword(self, name="Test Keyword"):
        return Keyword.objects.get_or_create(name=name)[0]

    def create_experience(self, exp_status, attendance=0):
        """Creates and returns an experience object with status,
        start_time, end_time and/or name of your choice"""
        return Experience.objects.get_or_create(
            author=self.clients['ra'].user_object,
            name="Test Experience",
            description="test description",
            start_datetime=self.test_date,
            end_datetime=(self.test_date + timedelta(days=1)),
            type=self.create_type(),
            sub_type=self.create_sub_type(),
            goal="Test Goal",
            audience="b",
            status=exp_status,
            attendance=attendance,
            next_approver=self.clients['ra'].user_object,
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

    def test_organization_str_method(self):
        o = self.create_org()
        self.assertEqual(str(Organization.objects.get(pk=o.pk)), o.name,
                         "Organization object should have been created.")

    def test_keyword_str_method(self):
        k = self.create_keyword()
        self.assertEqual(str(Keyword.objects.get(pk=k.pk)), k.name, "Keyword object should have been created.")

    def test_experience_str_method(self):
        e = self.create_experience('dr')
        self.assertEqual(str(Experience.objects.get(pk=e.pk)), e.name, "Experience object should have been created.")

    def test_experience_comment_message(self):
        ec = self.create_experience_comment(self.create_experience('de'))
        self.assertEqual(ExperienceComment.objects.get(pk=ec.pk).message, ec.message,
                         "ExperienceComment object should have been created.")

    def test_experience_needs_evaluation(self):
        e = self.create_experience('ad')
        self.assertTrue(e.needs_evaluation(), "This experience should return true for needs evaluation.")


class ExperienceCreationFormTest(StandardTestCase):

    def setUp(self):
        StandardTestCase.setUp(self)
        self.test_type = self.create_type()
        self.test_past_type = self.create_type(needs_verification=False)
        self.test_sub_type = self.create_sub_type()
        self.test_org = self.create_org()
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
                'goal': 'test'}

    def test_valid_experience_creation_form(self):
        data = self.get_post_data((self.test_date + timedelta(days=1)), (self.test_date + timedelta(days=2)))
        form = ExperienceSubmitForm(data, when=self.test_date)
        self.assertTrue(form.is_valid(), "Form should have been valid")

    def test_valid_past_experience_creation(self):
        data = self.get_post_data((self.test_date - timedelta(days=2)), (self.test_date - timedelta(days=1)))
        data['attendance'] = 1
        data['type'] = self.test_past_type.pk
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


class ExperienceCreationViewTest(StandardTestCase):

    def setUp(self):
        StandardTestCase.setUp(self)
        self.test_type = self.create_type()
        self.test_past_type = self.create_type(needs_verification=False)
        self.test_sub_type = self.create_sub_type()
        self.test_org = self.create_org()
        self.test_keyword = self.create_keyword()

    def get_post_data(self, start, end, action='submit'):
        return {'start_datetime_month': start.month,
                'start_datetime_day': start.day,
                'start_datetime_year': start.year,
                'end_datetime_month': end.month,
                'end_datetime_day': end.day,
                'end_datetime_year': end.year,
                'name': 'test',
                'description': 'test',
                'type': self.test_type.pk,
                'sub_type': self.test_sub_type.pk,
                'audience': 'c',
                'guest': 'test',
                'recognition': [self.test_org.pk],
                'keywords': [self.test_keyword.pk],
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
        self.clients['ra'].post(reverse('create_experience'), data)
        self.assertEqual('ad', Experience.objects.get(name='test').status,
                         "Experience should have been saved with approved status")


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
        response = self.clients['ra'].get(reverse('ra_home'))
        self.assertEqual(len(response.context["experiences"]), 2, "There should be 2 experiences displayed")

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
        response = self.clients['ra'].get(reverse('ra_home'))
        self.assertEqual(len(response.context["week_ahead"]), 1, "There should be 1 experience in the next week")


class ExperienceApprovalViewTest(StandardTestCase):

    def test_gets_correct_experience(self):
        e = self.create_experience('pe')
        self.create_experience('pe')
        response = self.clients['ra'].get(reverse('approval', args=[e.pk]))
        self.assertEqual(response.context['experience'].pk, e.pk, "The correct experience was not retrieved.")

    def test_404_when_experience_not_pending(self):
        e = self.create_experience('dr')
        response = self.clients['ra'].get(reverse('approval', args=[e.pk]))
        self.assertEqual(
            response.status_code,
            404,
            "Attempting to retrieve a non-pending experience did not generate a 404.")

    def test_does_not_allow_deny_without_comment(self):
        e = self.create_experience('pe')
        self.clients['ra'].post(reverse('approval', args=[e.pk]), {'deny': 'deny', 'message': ""})
        e = Experience.objects.get(pk=e.pk)
        self.assertEqual(e.status, 'pe', "An experience cannot be denied without a comment.")

    def test_approves_experience_no_comment(self):
        e = self.create_experience('pe')
        self.clients['ra'].post(reverse('approval', args=[e.pk]), {'approve': 'approve', 'message': ""})
        e = Experience.objects.get(pk=e.pk)
        self.assertEqual(e.status, 'ad', "Approval should be allowed without a comment")

    def test_approves_experience_with_comment(self):
        e = self.create_experience('pe')
        self.clients['ra'].post(reverse('approval', args=[e.pk]), {'approve': 'approve', 'message': "Test Comment"})
        e = Experience.objects.get(pk=e.pk)
        self.assertEqual(e.status, 'ad', "Approval should be allowed with a comment")

    def test_creates_comment(self):
        e = self.create_experience('pe')
        self.clients['ra'].post(reverse('approval', args=[e.pk]), {'deny': 'deny', 'message': "Test Comment"})
        comments = ExperienceComment.objects.filter(experience=e)
        self.assertEqual(len(comments), 1, "A comment should have been created.")

    def test_does_not_create_comment(self):
        e = self.create_experience('pe')
        self.clients['ra'].post(reverse('approval', args=[e.pk]), {'deny': 'deny', 'message': ""})
        comments = ExperienceComment.objects.filter(experience=e)
        self.assertEqual(
            len(comments),
            0,
            "If message is an empty string, no ExperienceComment object should be created.")


class HallStaffDashboardViewTest(StandardTestCase):

    def test_get_user(self):
        self.create_experience('pe')
        self.create_experience('dr')
        response = self.clients['ra'].get(reverse('hallstaff_dash'))
        self.assertEqual(
            response.context["user"].pk,
            self.clients['ra'].user_object.pk,
            "The correct user was not retrieved!"
        )


class LoginViewTest(StandardTestCase):
    credentials = ('username', 'a@a.com', 'password')

    @classmethod
    def setUpClass(cls):
        super(LoginViewTest, cls).setUpClass()
        get_user_model().objects.create_user(*cls.credentials)

    def test_login_success(self):
        username, _, password = self.credentials
        response = Client().post(reverse('login'), {'username': username, 'password': password})
        self.assertRedirects(response, reverse('welcome'))

    def test_login_failure(self):
        username, _, password = self.credentials
        c = Client()
        c.post(reverse('login'), {'username': username, 'password': password + 'wrong'})
        self.assertNotIn('_auth_user_id', c.session)

    def test_unauthorized_access_redirects_login(self):
        response = Client().get(reverse('welcome'))
        self.assertEqual(response.url.split('?')[0], reverse('login'))
