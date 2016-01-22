import copy
import json
import tempfile
import os
import re
import subprocess
import socket
import selenium
from selenium import webdriver
from selenium.webdriver.common.by import By
from django.core.urlresolvers import reverse
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.test.runner import DiscoverRunner
from django.utils.translation import ugettext as _
from django.utils.timezone import now, datetime, timedelta, make_aware, utc
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.conf import settings

from exdb.models import Experience, Type, SubType, Organization, Keyword
from exdb.forms import ExperienceSubmitForm


class CustomRunner(DiscoverRunner):
    _do_coverage = False

    def __init__(self, *args, **kwargs):
        # running DiscoverRunner constructor for default behavior
        super(self.__class__, self).__init__(*args, **kwargs)

        # deciding which driver to use
        drivers = self.get_drivers()
        browser_arg = kwargs.get('browser')
        if browser_arg:
            driver_obj = drivers.get(browser_arg)
            if not driver_obj:
                error = _('Unknown browser %(argument)s\nThe known browsers are: %(browsers)s')
                raise ValueError(error % {'argument': browser_arg, 'browsers': ', '.join(drivers.keys())})
        else:
            default_driver = 'phantomjs'
            driver_obj = drivers.get(default_driver)
        self.__class__.browser_driver = lambda: driver_obj.driver(*getattr(driver_obj, 'args', []))

        # setting the server location since the location may be relative to a remote host
        # if it looks like 0.0.0.0:\d+ then we should change the

        # default from the docs
        live_server_url = 'http://localhost:8081'
        os_address_key = 'DJANGO_LIVE_TEST_SERVER_ADDRESS'
        if os.environ.get(os_address_key):
            port_regex = r'0(\.0){3}:(?P<port>\d+)$'
            match = re.match(port_regex, os.environ[os_address_key])
            if match:
                live_server_url = 'http://' + socket.gethostname() + ':' + match.groupdict()['port']
        self.__class__.live_server_url = live_server_url

        if kwargs.get('coverage'):
            IstanbulCoverage.instrument_istanbul()
            self._do_coverage = True

    def teardown_test_environment(self, **kwargs):
        if self._do_coverage:
            IstanbulCoverage.output_coverage(DefaultLiveServerTestCase.running_total.coverage_files)
        super(self.__class__, self).teardown_test_environment(**kwargs)

    def get_drivers(self):
        chrome = lambda: 'chrome'
        chrome.driver = webdriver.Chrome

        edge = lambda: 'edge'
        edge.driver = webdriver.Edge

        firefox = lambda: 'firefox'
        firefox.driver = webdriver.Firefox

        ie = lambda: 'ie'
        ie.driver = webdriver.Ie

        phantomjs = lambda: 'phantomjs'
        phantomjs.driver = webdriver.PhantomJS

        remote = lambda: 'remote'
        remote.driver = webdriver.Remote
        capabilities = {
            'chromeOptions': {
                'androidPackage': 'com.android.chrome',
            }
        }
        remote_webdriver_server = 'http://localhost:9515'
        remote.args = (remote_webdriver_server, capabilities)

        return {
            'chrome': chrome,
            'edge': edge,
            'firefox': firefox,
            'ie': ie,
            'phantomjs': phantomjs,
            'remote': remote,
        }

    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument('-b', '--browser')
        parser.add_argument('-c', '--coverage', action='store_true')


class IstanbulCoverage(object):
    # this class assumes that the mappings for a file will not change during a single test run

    # the counting keys
    count_keys = ['s', 'b', 'f']

    def __init__(self):
        self.coverage_files = {}

    def _combine_count(self, x, y):
        """takes two dictionaries with values that are either ints or lists of ints and returns a similar structure with
        the sum of similarly nested integers

        the dictionaries are assumed to have the same keys as one another and the nested lists are assumed to be of the same length
        """
        result = {}
        assert type(x) is type(y) is dict
        for key, value in x.items():
            if isinstance(value, int):
                result[key] = y[key] + value
            elif isinstance(value, list):
                result[key] = [value[i] + y[key][i] for i in range(len(x))]

        return result

    def _dict_add(self, operand_coverage_files):
        # the operand files need be what is iterated over since the aggregated object will likely know about many more files than the operand
        # also the operand will likely know of things to be added
        for filename, operand_file_cov in operand_coverage_files.items():
            current_file_cov = self.coverage_files.get(filename)
            if not current_file_cov:
                self.coverage_files[filename] = copy.deepcopy(operand_file_cov)
            else:
                for count_key in self.count_keys:
                    self.coverage_files[filename][count_key] = self._combine_count(
                        operand_file_cov[count_key], current_file_cov[count_key])

    def __iadd__(self, operand):
        if isinstance(operand, dict):
            self._dict_add(operand)
        elif isinstance(operand, self.__class__):
            self._dict_add(operand.coverage_files)
        else:
            raise TypeError("unsupported operand type(s) for +: '%s' and '%s'" %
                            (self.__class__.__name__, operand.__class__.__name__))
        return self

    @classmethod
    def output_coverage(cls, coverage_files):
        f = tempfile.NamedTemporaryFile('w')
        f.write(json.dumps(coverage_files))
        f.flush()

        args = ['istanbul', 'report', '--include=' + f.name]
        subprocess.run(args + ['text-summary'])
        subprocess.run(args + ['html'])

        f.close()

    @classmethod
    def instrument_istanbul(cls):
        # this copies all information in the static directory to a new directory and replaces
        # all js files with an istanbul instrumented version of it
        instrumented_static = 'instrumented_static'
        app_root = os.path.dirname(__file__)

        settings.STATICFILES_DIRS = [os.path.join(app_root, instrumented_static)]
        # this could be made to accept many different directories
        # for now it is just the default "static/"
        exclusions = [['-x', '**/%s/**' % s] for s in settings.JS_FILE_EXCLUDED_DIRS]
        # flatten into a single list for arguments
        exclusions = [item for items in exclusions for item in items]

        istanbul_process = subprocess.run(
            [
                'istanbul',
                'instrument', os.path.join(app_root, 'static'),
                '--output', os.path.join(app_root, instrumented_static)
            ] + exclusions)

        if istanbul_process.returncode != 0:
            raise Exception('Instrumentation failed')


class DefaultLiveServerTestCase(StaticLiveServerTestCase):
    running_total = IstanbulCoverage()

    def setUp(self):
        self.driver = CustomRunner.browser_driver()

    def tearDown(self):
        try:
            self.running_total += self.driver.execute_script('return __coverage__')
        except selenium.common.exceptions.WebDriverException:
            pass  # if __coverage__ doesn't exist ignore it and move on


class SeleniumJSCoverage(DefaultLiveServerTestCase):

    def test_load(self):
        self.driver.get(CustomRunner.live_server_url)
        self.assertEqual(self.driver.find_element(By.XPATH, '//h1').text, _('Welcome'))

    def test_something_else(self):
        self.driver.get(CustomRunner.live_server_url)
        self.assertEqual(self.driver.find_element(By.XPATH, '//h1').text, _('Welcome'))
        self.driver.execute_script('f()')


class WelcomeViewTest(DefaultLiveServerTestCase):

    def test_load(self):
        self.driver.get(CustomRunner.live_server_url)
        self.assertEqual(self.driver.find_element(By.XPATH, '//h1').text, _('Welcome'))


class PendingApprovalQueueBrowserTest(DefaultLiveServerTestCase):

    def test_load(self):
        self.driver.get(CustomRunner.live_server_url + reverse('pending'))
        self.assertEqual(self.driver.find_element(By.XPATH, '//h1').text, _('Experiences Pending Approval'))


###################### Integration Tests #########################

class StandardTestCase(TestCase):

    def setUp(self):
        self.test_user = get_user_model().objects.create_user('test_user', 't@u.com', 'a')
        self.test_date = make_aware(datetime(2015, 1, 1, 1, 30), timezone=utc)
        self.test_type = self.create_type()
        self.test_past_type = self.create_type(needs_verification=False)
        self.test_sub_type = self.create_sub_type()
        self.test_org = self.create_org()
        self.test_keyword = Keyword.objects.create(name="test")

    def create_type(self, needs_verification=True):
        return Type.objects.create(name="Test Type", needs_verification=needs_verification)

    def create_sub_type(self):
        return SubType.objects.create(name="Test Sub Type")

    def create_org(self):
        return Organization.objects.create(name="Test Organization")

    def create_experience(self, exp_status):
        """Creates and returns an experience object with status of your choice"""
        return Experience.objects.create(author=self.test_user, name="E1", description="test description", start_datetime=self.test_date,
                                         end_datetime=(self.test_date + timedelta(days=1)), type=self.create_type(), sub_type=self.create_sub_type(), goal="Test Goal", audience="b",
                                         status=exp_status)


class PendingApprovalQueueViewTest(StandardTestCase):

    def test_get_pending_queues(self):
        self.create_experience('pe')
        self.create_experience('dr')
        client = Client()
        response = client.get(reverse('pending'))
        self.assertEqual(len(response.context["experiences"]), 1, "Only pending queues should be returned")

    def test_does_not_get_spontaneous(self):
        Experience.objects.create(author=self.test_user, name="E1", description="test description", start_datetime=(self.test_date - timedelta(days=2)),
                                  end_datetime=(self.test_date - timedelta(days=1)), type=self.create_type(), sub_type=self.create_sub_type(), goal="Test Goal", audience="b",
                                  status="co", attendance=3)
        client = Client()
        response = client.get(reverse('pending'))
        self.assertEqual(len(response.context["experiences"]), 0, "Spontaneous experiences should not be returned")


class ExperienceCreationFormTest(StandardTestCase):

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

    def test_valid_future_experience_creation_view_submit(self):
        c = Client()
        start = now() + timedelta(days=1)
        end = now() + timedelta(days=2)
        c.login(username="test_user", password='a')
        data = {'name': 'test', 'description': 'test', 'start_datetime_month': start.month,
                'start_datetime_day': start.day, 'start_datetime_year': start.year,
                'end_datetime_month': end.month, 'end_datetime_day': end.day, 'end_datetime_year': end.year,
                'type': self.test_type.pk, 'sub_type': self.test_sub_type.pk, 'audience': 'c',
                'guest': '1', 'recognition': self.test_org.pk, 'keywords': self.test_keyword.pk, 'goal': 'a', 'submit': 'Submit'}
        c.post(reverse('create-experience'), data)
        self.assertEqual('pe', Experience.objects.get(name='test').status,
                         "Experience should have been saved with pending status")

    def test_valid_experience_creation_view_save(self):
        c = Client()
        start = now() + timedelta(days=1)
        end = now() + timedelta(days=2)
        c.login(username="test_user", password='a')
        data = {'name': 'test', 'description': 'test', 'start_datetime_month': start.month,
                'start_datetime_day': start.day, 'start_datetime_year': start.year,
                'end_datetime_month': end.month, 'end_datetime_day': end.day, 'end_datetime_year': end.year,
                'type': self.test_type.pk, 'sub_type': self.test_sub_type.pk, 'audience': 'c',
                'guest': '1', 'recognition': self.test_org.pk, 'keywords': self.test_keyword.pk, 'goal': 'a', 'save': 'Save'}
        c.post(reverse('create-experience'), data)
        self.assertEqual('dr', Experience.objects.get(name='test').status,
                         "Experience should have been saved with draft status")

    def test_valid_past_experience_creation_view_submit(self):
        c = Client()
        start = now() - timedelta(days=2)
        end = now() - timedelta(days=1)
        c.login(username="test_user", password='a')
        data = {'name': 'test', 'description': 'test', 'start_datetime_month': start.month,
                'start_datetime_day': start.day, 'start_datetime_year': start.year,
                'end_datetime_month': end.month, 'end_datetime_day': end.day, 'end_datetime_year': end.year,
                'type': self.test_past_type.pk, 'sub_type': self.test_sub_type.pk, 'audience': 'c', 'attendance': 1,
                'guest': '1', 'recognition': self.test_org.pk, 'keywords': self.test_keyword.pk, 'goal': 'a', 'submit': 'Submit'}
        c.post(reverse('create-experience'), data)
        self.assertEqual('co', Experience.objects.get(name='test').status,
                         "Experience should have been saved with completed status")
