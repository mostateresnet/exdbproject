from django.test import TestCase, Client
from django.utils.timezone import datetime, timedelta, now, make_aware, utc
from django.core.urlresolvers import reverse
from django.contrib.auth import get_user_model

from exdb.models import Experience, Type, SubType, Organization, Keyword, ExperienceComment, Category
from exdb.forms import ExperienceSubmitForm


class StandardTestCase(TestCase):

    def setUp(self):
        self.test_user = get_user_model().objects.create_user('test_user', 't@u.com', 'a')
        self.test_date = make_aware(datetime(2015, 1, 1, 1, 30), timezone=utc)
        self.anon_client = Client()
        self.login_client = Client()
        self.login_client.login(username='test_user', password='a')

    def create_type(self, needs_verification=True, name="Test Type"):
        return Type.objects.get_or_create(name=name, needs_verification=needs_verification)[0]

    def create_sub_type(self, name="Test Sub Type"):
        return SubType.objects.get_or_create(name=name)[0]

    def create_org(self, name="Test Organization"):
        return Organization.objects.get_or_create(name=name)[0]

    def create_keyword(self, name="Test Keyword"):
        return Keyword.objects.get_or_create(name=name)[0]

    def create_category(self, name="Test Category"):
        return Category.objects.get_or_create(name=name)[0]

    def create_experience(self, exp_status, name="Test Experience"):
        """Creates and returns an experience object with status of your choice"""
        return Experience.objects.get_or_create(author=self.test_user, name=name, description="test description", start_datetime=self.test_date,
                                                end_datetime=(self.test_date + timedelta(days=1)), type=self.create_type(), sub_type=self.create_sub_type(), goal="Test Goal", audience="b",
                                                status=exp_status)[0]

    def create_experience_comment(self, exp, message="Test message"):
        """Creates experience comment, must pass an experience"""
        return ExperienceComment.objects.get_or_create(
            experience=exp, message=message, author=self.test_user, timestamp=self.test_date)[0]


class ModelCoverageTest(StandardTestCase):

    def test_sub_type_str_method(self):
        st = self.create_sub_type()
        self.assertEqual(str(SubType.objects.get(pk=st.pk)), st.name,
                         "SubType object should have been created.")

    def test_type_str_method(self):
        t = self.create_type()
        self.assertEqual(str(Type.objects.get(pk=t.pk)), t.name, "Type object should have been created.")

    def test_category_str_method(self):
        c = self.create_category()
        self.assertEqual(str(Category.objects.get(pk=c.pk)), c.name,
                         "Category object should have been created.")

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


class ExperienceCreationFormTest(StandardTestCase):

    def setUp(self):
        StandardTestCase.setUp(self)
        self.test_type = self.create_type()
        self.test_past_type = self.create_type(needs_verification=False)
        self.test_sub_type = self.create_sub_type()
        self.test_org = self.create_org()
        self.test_keyword = self.create_keyword()

    def test_valid_experience_creation_form(self):
        data = {'name': 'test', 'description': 'test', 'start_datetime': (self.test_date + timedelta(days=1)),
                'end_datetime': (self.test_date + timedelta(days=2)), 'type': self.test_type.pk, 'sub_type': self.test_sub_type.pk, 'audience': 'c',
                'guest': '1', 'recognition': [self.test_org.pk], 'keywords': [self.test_keyword.pk], 'goal': 'a'}
        form = ExperienceSubmitForm(data, when=self.test_date)
        self.assertTrue(form.is_valid(), "Form should have been valid")

    def test_valid_past_experience_creation(self):
        data = {'name': 'test', 'description': 'test', 'start_datetime': (self.test_date - timedelta(days=2)),
                'end_datetime': (self.test_date - timedelta(days=1)), 'type': self.test_past_type.pk, 'sub_type': self.test_sub_type.pk, 'audience': 'c',
                'guest': '1', 'recognition': [self.test_org.pk], 'keywords': [self.test_keyword.pk], 'goal': 'a', 'attendance': 1}
        form = ExperienceSubmitForm(data, when=self.test_date)
        self.assertTrue(form.is_valid(), "Form should have been valid")

    def test_past_experience_without_audience(self):
        data = {'name': 'test', 'description': 'test', 'start_datetime': (self.test_date - timedelta(days=2)),
                'end_datetime': (self.test_date - timedelta(days=1)), 'type': self.test_past_type.pk, 'sub_type': self.test_sub_type.pk,
                'guest': '1', 'recognition': [self.test_org.pk], 'keywords': [self.test_keyword.pk], 'goal': 'a', 'attendance': 1}
        form = ExperienceSubmitForm(data, when=self.test_date)
        self.assertFalse(form.is_valid(), "Form should NOT have been valid")

    def test_past_experience_type_with_future_dates(self):
        data = {'name': 'test', 'description': 'test', 'start_datetime': (self.test_date + timedelta(days=1)),
                'end_datetime': (self.test_date + timedelta(days=2)), 'type': self.test_past_type.pk, 'sub_type': self.test_sub_type.pk, 'audience': 'c',
                'guest': '1', 'recognition': [self.test_org.pk], 'keywords': [self.test_keyword.pk], 'goal': 'a', 'attendance': 1}
        form = ExperienceSubmitForm(data, when=self.test_date)
        self.assertFalse(form.is_valid(), "Form should NOT have been valid")

    def test_future_experience_type_with_past_dates(self):
        data = {'name': 'test', 'description': 'test', 'start_datetime': (self.test_date - timedelta(days=2)),
                'end_datetime': (self.test_date - timedelta(days=1)), 'type': self.test_type.pk, 'sub_type': self.test_sub_type.pk, 'audience': 'c',
                'guest': '1', 'recognition': [self.test_org.pk], 'keywords': [self.test_keyword.pk], 'goal': 'a'}
        form = ExperienceSubmitForm(data, when=self.test_date)
        self.assertFalse(form.is_valid(), "Form should NOT have been valid")

    def test_future_experience_with_start_date_after_end_date(self):
        data = {'name': 'test', 'description': 'test', 'start_datetime': (self.test_date + timedelta(days=3)),
                'end_datetime': (self.test_date + timedelta(days=2)), 'type': self.test_type.pk, 'sub_type': self.test_sub_type.pk, 'audience': 'c',
                'guest': '1', 'recognition': [self.test_org.pk], 'keywords': [self.test_keyword.pk], 'goal': 'a'}
        form = ExperienceSubmitForm(data, when=self.test_date)
        self.assertFalse(form.is_valid(), "Form should NOT have been valid")

    def test_past_experience_creation_no_attendance(self):
        data = {'name': 'test', 'description': 'test', 'start_datetime': (self.test_date - timedelta(days=2)),
                'end_datetime': (self.test_date - timedelta(days=1)), 'type': self.test_past_type.pk, 'sub_type': self.test_sub_type.pk, 'audience': 'c',
                'guest': '1', 'recognition': [self.test_org.pk], 'keywords': [self.test_keyword.pk], 'goal': 'a'}
        form = ExperienceSubmitForm(data, when=self.test_date)
        self.assertFalse(form.is_valid(), "Form should NOT have been valid")

    def test_experience_creation_with_attendance(self):
        data = {'name': 'test', 'description': 'test', 'start_datetime': (self.test_date + timedelta(days=1)),
                'end_datetime': (self.test_date + timedelta(days=2)), 'type': self.test_type.pk, 'sub_type': self.test_sub_type.pk, 'audience': 'c',
                'guest': '1', 'recognition': [self.test_org.pk], 'keywords': [self.test_keyword.pk], 'goal': 'a', 'attendance': 1}
        form = ExperienceSubmitForm(data, when=self.test_date)
        self.assertFalse(form.is_valid(), "Form should NOT have been valid")

    def test_past_experience_creation_negative_attendance(self):
        data = {'name': 'test', 'description': 'test', 'start_datetime': (self.test_date - timedelta(days=2)),
                'end_datetime': (self.test_date - timedelta(days=1)), 'type': self.test_past_type.pk, 'sub_type': self.test_sub_type.pk, 'audience': 'c',
                'guest': '1', 'recognition': [self.test_org.pk], 'keywords': [self.test_keyword.pk], 'goal': 'a', 'attendance': -1}
        form = ExperienceSubmitForm(data, when=self.test_date)
        self.assertFalse(form.is_valid(), "Form should NOT have been valid")

    def test_experience_creation_form_no_end_date(self):
        data = {'name': 'test', 'description': 'test', 'start_datetime': (self.test_date + timedelta(days=1)),
                'type': self.test_type.pk, 'sub_type': self.test_sub_type.pk, 'audience': 'c',
                'guest': '1', 'recognition': [self.test_org.pk], 'keywords': [self.test_keyword.pk], 'goal': 'a'}
        form = ExperienceSubmitForm(data, when=self.test_date)
        self.assertFalse(form.is_valid(), "Form should NOT have been valid")

    def test_experience_creation_form_no_start_date(self):
        data = {'name': 'test', 'description': 'test', 'end_datetime': (self.test_date + timedelta(days=2)),
                'type': self.test_type.pk, 'sub_type': self.test_sub_type.pk, 'audience': 'c',
                'guest': '1', 'recognition': [self.test_org.pk], 'keywords': [self.test_keyword.pk], 'goal': 'a'}
        form = ExperienceSubmitForm(data, when=self.test_date)
        self.assertFalse(form.is_valid(), "Form should NOT have been valid")

    def test_experience_creation_form_no_sub_type(self):
        data = {'name': 'test', 'description': 'test', 'start_datetime': (self.test_date + timedelta(days=1)),
                'end_datetime': (self.test_date + timedelta(days=2)), 'type': self.test_type.pk, 'audience': 'c',
                'guest': '1', 'recognition': [self.test_org.pk], 'keywords': [self.test_keyword.pk], 'goal': 'a'}
        form = ExperienceSubmitForm(data, when=self.test_date)
        self.assertFalse(form.is_valid(), "Form should NOT have been valid")

    def test_experience_creation_form_no_type(self):
        data = {'name': 'test', 'description': 'test', 'start_datetime': (self.test_date + timedelta(days=1)),
                'end_datetime': (self.test_date + timedelta(days=2)), 'sub_type': self.test_sub_type.pk, 'audience': 'c',
                'guest': '1', 'recognition': [self.test_org.pk], 'keywords': [self.test_keyword.pk], 'goal': 'a'}
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

    def test_valid_future_experience_creation_view_submit(self):
        start = now() + timedelta(days=1)
        end = now() + timedelta(days=2)
        data = {'name': 'test', 'description': 'test', 'start_datetime_month': start.month,
                'start_datetime_day': start.day, 'start_datetime_year': start.year,
                'end_datetime_month': end.month, 'end_datetime_day': end.day, 'end_datetime_year': end.year,
                'type': self.test_type.pk, 'sub_type': self.test_sub_type.pk, 'audience': 'c',
                'guest': '1', 'recognition': self.test_org.pk, 'keywords': self.test_keyword.pk, 'goal': 'a', 'submit': 'Submit'}
        self.login_client.post(reverse('create-experience'), data)
        self.assertEqual('pe', Experience.objects.get(name='test').status,
                         "Experience should have been saved with pending status")

    def test_valid_experience_creation_view_save(self):
        start = now() + timedelta(days=1)
        end = now() + timedelta(days=2)
        data = {'name': 'test', 'description': 'test', 'start_datetime_month': start.month,
                'start_datetime_day': start.day, 'start_datetime_year': start.year,
                'end_datetime_month': end.month, 'end_datetime_day': end.day, 'end_datetime_year': end.year,
                'type': self.test_type.pk, 'sub_type': self.test_sub_type.pk, 'audience': 'c',
                'guest': '1', 'recognition': self.test_org.pk, 'keywords': self.test_keyword.pk, 'goal': 'a', 'save': 'Save'}
        self.login_client.post(reverse('create-experience'), data)
        self.assertEqual('dr', Experience.objects.get(name='test').status,
                         "Experience should have been saved with draft status")

    def test_valid_past_experience_creation_view_submit(self):
        start = now() - timedelta(days=2)
        end = now() - timedelta(days=1)
        data = {'name': 'test', 'description': 'test', 'start_datetime_month': start.month,
                'start_datetime_day': start.day, 'start_datetime_year': start.year,
                'end_datetime_month': end.month, 'end_datetime_day': end.day, 'end_datetime_year': end.year,
                'type': self.test_past_type.pk, 'sub_type': self.test_sub_type.pk, 'audience': 'c', 'attendance': 1,
                'guest': '1', 'recognition': self.test_org.pk, 'keywords': self.test_keyword.pk, 'goal': 'a', 'submit': 'Submit'}
        self.login_client.post(reverse('create-experience'), data)
        self.assertEqual('co', Experience.objects.get(name='test').status,
                         "Experience should have been saved with completed status")


class RAHomeViewTest(StandardTestCase):

    def test_coverage(self):
        self.create_experience('pe')
        self.create_experience('dr')
        client = Client()
        client.login(username="test_user", password="a")
        response = client.get(reverse('ra_home'))
        self.assertEqual(len(response.context["experiences"]), 2, "There should be 2 experiences displayed")


class PendingApprovalQueueViewTest(StandardTestCase):

    def test_get_pending_queues(self):
        self.create_experience('pe')
        self.create_experience('dr')
        response = self.anon_client.get(reverse('pending'))
        self.assertEqual(len(response.context["experiences"]), 1, "Only pending queues should be returned")

    def test_does_not_get_spontaneous(self):
        Experience.objects.create(author=self.test_user, name="E1", description="test description", start_datetime=(self.test_date - timedelta(days=2)),
                                  end_datetime=(self.test_date - timedelta(days=1)), type=self.create_type(), sub_type=self.create_sub_type(), goal="Test Goal", audience="b",
                                  status="co", attendance=3)
        response = self.anon_client.get(reverse('pending'))
        self.assertEqual(len(response.context["experiences"]), 0, "Spontaneous experiences should not be returned")
