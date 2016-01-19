from django.test import TestCase, Client
from django.utils.timezone import datetime, timedelta, make_aware, utc
from django.core.urlresolvers import reverse
from django.contrib.auth import get_user_model

from exdb.models import Experience, Type, SubType, Organization


class StandardTestCase(TestCase):
    def setUp(self):
        self.test_user = get_user_model().objects.create_user('test_user', 't@u.com', 'a')
        self.test_date = make_aware(datetime(2015, 1, 1, 1, 30), timezone=utc)
        self.anon_client = Client()
        self.login_client = Client()
        self.login_client.login(username='test_user', password='a')

    def create_type(self):
        return Type.objects.create(name="Test Type")

    def create_sub_type(self):
        return SubType.objects.create(name="Test Sub Type")

    def create_org(self):
        return Organization.objects.create(name="Test Organization")

    def create_experience(self, exp_status):
        """Creates and returns an experience object with status of your choice"""
        return Experience.objects.create(author=self.test_user, name="E1", description="test description", start_datetime=self.test_date,\
                end_datetime=(self.test_date + timedelta(days=1)), type=self.create_type(), sub_type=self.create_sub_type(), goal="Test Goal", audience="b", \
                 status=exp_status)

class PendingApprovalQueueViewTest(StandardTestCase):
    def test_get_pending_queues(self):
        self.create_experience('pe')
        self.create_experience('dr')
        response = self.anon_client.get(reverse('pending'))
        self.assertEqual(len(response.context["experiences"]), 1, "Only pending queues should be returned")

    def test_does_not_get_spontaneous(self):
        Experience.objects.create(author=self.test_user, name="E1", description="test description", start_datetime=(self.test_date - timedelta(days=2)),\
                end_datetime=(self.test_date - timedelta(days=1)), type=self.create_type(), sub_type=self.create_sub_type(), goal="Test Goal", audience="b", \
                 status="co", attendance=3)
        response = self.anon_client.get(reverse('pending'))
        self.assertEqual(len(response.context["experiences"]), 0, "Spontaneous experiences should not be returned")
