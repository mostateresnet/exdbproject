import os
import socket
import re
import subprocess
import tempfile
import copy
import json
from unittest import SkipTest

import selenium
from selenium import webdriver
from selenium.webdriver.common.by import By

from django.test import Client
from django.test.runner import DiscoverRunner
from django.utils.translation import ugettext as _
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.conf import settings
from django.core.urlresolvers import reverse
from exdb.models import Type


class CustomRunnerMetaClass(type):

    @property
    def perma_driver(cls):
        # lazily intiate browser driver
        if not hasattr(cls, '_perma_driver'):
            cls._perma_driver = CustomRunner.browser_driver()
        return cls._perma_driver

    def exit_perma_driver(cls):
        # exit driver if it has been started
        if hasattr(cls, '_perma_driver'):
            cls._perma_driver.quit()


class CustomRunner(DiscoverRunner, metaclass=CustomRunnerMetaClass):
    _do_coverage = False
    skip_browser_tests = False

    def __init__(self, *args, **kwargs):
        # running DiscoverRunner constructor for default behavior
        super(self.__class__, self).__init__(*args, **kwargs)

        # deciding which driver to use
        drivers = self.get_drivers()

        browser_arg = kwargs.get('browser')
        if browser_arg == 'none':
            CustomRunner.skip_browser_tests = True  # pragma: no cover

        if browser_arg:  # pragma: no cover
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
        if os.environ.get(os_address_key):  # pragma: no cover
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
        self.__class__.exit_perma_driver()

    def get_drivers(self):
        chrome = lambda: 'chrome'
        chrome.driver = webdriver.Chrome

        edge = lambda: 'edge'
        edge.driver = webdriver.Edge

        firefox = lambda: 'firefox'
        firefox.driver = webdriver.Firefox

        ie = lambda: 'ie'
        ie.driver = webdriver.Ie

        none_obj = lambda: 'none'
        none_obj.driver = 'none'

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
            'none': none_obj,
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
                result[key] = [value[i] + y[key][i] for i in range(len(value))]

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
        elif isinstance(operand, self.__class__):  # pragma: no cover
            self._dict_add(operand.coverage_files)
        else:  # pragma: no cover
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
        app_root = os.path.join(os.path.dirname(__file__), '..')

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

        if istanbul_process.returncode != 0:  # pragma: no cover
            raise Exception('Instrumentation failed')


class DefaultLiveServerTestCase(StaticLiveServerTestCase):
    running_total = IstanbulCoverage()

    @classmethod
    def setUpClass(cls):
        if CustomRunner.skip_browser_tests:
            raise SkipTest('Skipped due to argument')  # pragma: no cover
        super(DefaultLiveServerTestCase, cls).setUpClass()

    class SeleniumClient:

        def __init__(self, driver):
            self.driver = driver

        def get(self, url):
            self.driver.get(CustomRunner.live_server_url + url)

        def force_login(self):
            'Login a browser without visiting the login page'
            c = Client()
            # avoid setting the password and force_login for speed
            user_object = get_user_model().objects.create(username='user')
            c.force_login(user_object)
            if CustomRunner.live_server_url not in self.driver.current_url:
                # if we would be trying to set a cross domain cookie change the domain
                self.get(reverse('login'))

            cookie = {'name': 'sessionid', 'value': c.session.session_key}
            try:
                self.driver.add_cookie(cookie)
            except selenium.common.exceptions.WebDriverException:
                # phantomjs has a bug claiming it cannot set the cookie
                # it actually does set the cookie
                # check that it is there and continue if it is
                for c in self.driver.get_cookies():
                    if c['value'] == cookie['value']:
                        break
                else:
                    raise Exception('Cookie could not be set')  # pragma: no cover

    def get_client_and_driver(self):
        self.driver = CustomRunner.perma_driver
        self.client = self.SeleniumClient(self.driver)

    def setUp(self):
        self.get_client_and_driver()
        self.client.force_login()

    def tearDown(self):
        try:
            self.running_total += self.driver.execute_script('return __coverage__')
        except selenium.common.exceptions.WebDriverException:  # pragma: no cover
            pass  # if __coverage__ doesn't exist ignore it and move on
        self.driver.delete_all_cookies()


class LiveLoginViewTest(DefaultLiveServerTestCase):

    def setUp(self):
        # the super class setup logs us in without the page
        self.get_client_and_driver()

    def test_login(self):
        username = 'test'
        password = 'test'

        # create user object
        user_object = get_user_model().objects.create(username=username)
        user_object.set_password(password)
        user_object.save()
        self.client.get(reverse('login'))

        # actually login
        driver = self.client.driver
        driver.find_element_by_css_selector('[type=text]').send_keys(username)
        driver.find_element_by_css_selector('[type=password]').send_keys(password)
        driver.find_element_by_css_selector('[type=submit]').click()

        # check if we are logged in
        is_logged_in = False
        for c in driver.get_cookies():
            if c['name'] == 'sessionid':
                is_logged_in = bool(Session.objects.filter(session_key=c['value']))

        self.assertTrue(is_logged_in)


class WelcomeViewTest(DefaultLiveServerTestCase):

    def test_load(self):
        self.client.get('/')
        self.assertEqual(self.driver.find_element(By.XPATH, '//h1').text, _('Welcome'))


class HallStaffDashboardBrowserTest(DefaultLiveServerTestCase):

    def test_load(self):
        self.client.get(reverse('hallstaff_dash'))
        self.assertEqual(self.driver.find_element(By.XPATH, '//h1').text, _('Experiences Pending Approval'))


class CreateExperienceBrowserTest(DefaultLiveServerTestCase):

    def create_spontaneous_type(self):
        return Type.objects.create(name="Spontaneous", needs_verification=False)

    def test_attendance_hidden(self):
        self.client.get(reverse('create_experience'))
        attnd_element = self.driver.find_element(By.ID, 'id_attendance')
        self.assertFalse(attnd_element.find_element(By.XPATH, '..').is_displayed(),
                         'Attendance field should be hidden on load.')

    def test_shows_attendance_field(self):
        self.create_spontaneous_type()
        self.client.get(reverse('create_experience'))
        type_element = self.driver.find_element(By.ID, 'id_type')
        type_element.find_element_by_class_name('no-verification').click()
        attnd_element = self.driver.find_element(By.ID, 'id_attendance')
        self.assertTrue(attnd_element.find_element(By.XPATH, '..').is_displayed(),
                        'Attendance field should not be hidden when spontaneous is selected.')

    def test_rehides_attendance_field(self):
        self.create_spontaneous_type()
        self.client.get(reverse('create_experience'))
        type_element = self.driver.find_element(By.ID, 'id_type')
        type_element.find_element_by_class_name('no-verification').click()
        type_element.find_elements_by_tag_name('option')[0].click()
        attnd_element = self.driver.find_element(By.ID, 'id_attendance')
        self.assertFalse(attnd_element.find_element(By.XPATH, '..').is_displayed(),
                         'Attendance field should be hidden when spontaneous is not selected.')
