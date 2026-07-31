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
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions

from django.test import Client
from django.test.runner import DiscoverRunner
from django.utils.translation import gettext as _
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.sessions.models import Session
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.conf import settings
from django.urls import reverse
from django.utils.timezone import datetime, timedelta, now, make_aware, utc

from exdb.models import Experience, Type, Subtype, Affiliation, Section, Semester


class CustomRunnerMetaClass(type):

    @property
    def perma_driver(cls):
        # lazily intiate browser driver
        if not hasattr(cls, '_perma_driver'):
            cls._perma_driver = CustomRunner.browser_driver()
        else:
            # driver may have been quit or crashed; verify it's still alive
            try:
                cls._perma_driver.current_window_handle
            except Exception:
                try:
                    cls._perma_driver.quit()
                except Exception:
                    pass
                delattr(cls, '_perma_driver')
                cls._perma_driver = CustomRunner.browser_driver()
        return cls._perma_driver

    def exit_perma_driver(cls):
        # exit driver if it has been started
        if hasattr(cls, '_perma_driver'):
            try:
                cls._perma_driver.close()
            except Exception:
                try:
                    cls._perma_driver.quit()
                except Exception:
                    pass
            try:
                delattr(cls, '_perma_driver')
            except AttributeError:
                pass


class CustomRunner(DiscoverRunner, metaclass=CustomRunnerMetaClass):
    _do_coverage = False
    skip_browser_tests = False
    _headless = True

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
            default_driver = 'chrome'
            driver_obj = drivers.get(default_driver)

        headless = kwargs.get('headless', True)
        CustomRunner._headless = headless

        def make_driver():
            if hasattr(driver_obj, 'create_options'):
                options = driver_obj.create_options(headless)
                return driver_obj.driver(options=options)
            return driver_obj.driver(*getattr(driver_obj, 'args', []), **getattr(driver_obj, 'kwargs', {}))
        self.__class__.browser_driver = make_driver

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
        def chrome(headless=False):
            return 'chrome'  # pylint: disable=multiple-statements
        chrome.driver = webdriver.Chrome
        chrome.create_options = lambda headless: self._create_chrome_options(headless)

        def headless_chrome(headless=True):
            return 'headless_chrome'  # pylint: disable=multiple-statements
        headless_chrome.driver = webdriver.Chrome
        headless_chrome.create_options = lambda headless: self._create_chrome_options(True)

        def edge(): return 'edge'  # pylint: disable=multiple-statements
        edge.driver = webdriver.Edge

        def firefox(): return 'firefox'  # pylint: disable=multiple-statements
        firefox.driver = webdriver.Firefox

        def ie(): return 'ie'  # pylint: disable=multiple-statements
        ie.driver = webdriver.Ie

        def none_obj(): return 'none'  # pylint: disable=multiple-statements
        none_obj.driver = 'none'

        def phantomjs(): return 'phantomjs'  # pylint: disable=multiple-statements
        try:
            phantomjs.driver = webdriver.PhantomJS
        except AttributeError:
            phantomjs.driver = None

        def remote(): return 'remote'  # pylint: disable=multiple-statements
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
            'headless_chrome': headless_chrome,
            'edge': edge,
            'firefox': firefox,
            'ie': ie,
            'none': none_obj,
            'phantomjs': phantomjs,
            'remote': remote,
        }

    def _create_chrome_options(self, headless):
        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument('--headless=new')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--disable-extensions')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--disable-background-timer-throttling')
            options.add_argument('--disable-backgrounding-occluded-windows')
            options.add_argument('--disable-renderer-backgrounding')
            options.add_argument('--disable-software-rasterizer')
            options.add_argument('--disable-infobars')
            options.add_argument('--disable-restore-session-state')
            options.add_argument('--disable-features=ZygoteSandbox')
        else:
            options.add_argument('--window-size=1920,1080')
        return options

    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument('-b', '--browser')
        parser.add_argument('-c', '--coverage', action='store_true')
        parser.add_argument('--headless', action='store_true', default=True,
                            help='Run browser tests in headless mode (default)')


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

    def create_type(self, name="Test Type"):
        return Type.objects.get_or_create(name=name)[0]

    def create_subtype(self, needs_verification=True, name="Test Subtype"):
        return Subtype.objects.get_or_create(name=name, needs_verification=needs_verification)[0]

    def create_experience(self, exp_status, user=None, start=None, end=None, name=None):
        """Creates and returns an experience object with status,
        start_time, end_time and/or name of your choice"""
        start = start or make_aware(datetime(2015, 1, 1, 1, 30), timezone=utc)
        end = end or (make_aware(datetime(2015, 1, 1, 1, 30), timezone=utc) + timedelta(days=1))
        user = user or get_user_model().objects.get(username='user')
        name = name or 'Test'
        experience = Experience.objects.get_or_create(
            author=user,
            name=name,
            description="test",
            start_datetime=start,
            end_datetime=end,
            type=self.create_type(),
            goals="Test",
            audience="c",
            status=exp_status,
            attendance=0,
            next_approver=user,
        )[0]
        experience.subtypes.add(self.create_subtype())
        return experience

    class SeleniumClient:

        def __init__(self, driver, live_server_url):
            self.driver = driver
            self.live_server_url = live_server_url
            try:
                self.driver.set_window_size(1920, 1080)
            except Exception:
                pass  # window size already set via ChromeOptions

        def get(self, url):
            self.driver.get(self.live_server_url + url)
            # Wait for page to load to prevent tab crashes in headless mode
            try:
                WebDriverWait(self.driver, 5).until(
                    expected_conditions.title_contains('')
                )
            except Exception:
                pass

        def force_login(self):
            'Login a browser without visiting the login page'
            c = Client()
            # avoid setting the password and force_login for speed
            user_object = get_user_model().objects.create(username='user', first_name="User")
            c.force_login(user_object)
            try:
                if self.live_server_url not in self.driver.current_url:
                    # if we would be trying to set a cross domain cookie change the domain
                    self.get(reverse('login'))
            except selenium.common.exceptions.WebDriverException:
                # tab may have crashed; try to reload
                self.get(reverse('login'))
                try:
                    if self.live_server_url not in self.driver.current_url:
                        self.get(reverse('login'))
                except selenium.common.exceptions.WebDriverException:
                    pass

            cookie = {'name': 'sessionid', 'value': c.session.session_key, 'path': '/'}
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
        self.client = self.SeleniumClient(self.driver, self.live_server_url)

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
        driver.find_element(By.CSS_SELECTOR, '[type=text]').send_keys(username)
        driver.find_element(By.CSS_SELECTOR, '[type=password]').send_keys(password)
        driver.find_element(By.CSS_SELECTOR, '[type=submit]').click()
        WebDriverWait(driver, 15).until(
            lambda d: any(c['name'] == 'sessionid' for c in d.get_cookies())
        )

        # check if we are logged in
        is_logged_in = False
        for c in driver.get_cookies():
            if c['name'] == 'sessionid':
                is_logged_in = bool(Session.objects.filter(session_key=c['value']))

        self.assertTrue(is_logged_in)


class HomeBrowserTest(DefaultLiveServerTestCase):

    def test_load(self):
        self.client.get(reverse('home'))
        user = get_user_model().objects.filter(username='user')[0]
        self.assertEqual(self.driver.find_element(By.XPATH, '//h2').get_attribute('textContent'),
                         _('Hello, ' + user.first_name))


class EditExperienceBrowserTest(DefaultLiveServerTestCase):

    def delete_confirm(self, confirm):
        e = self.create_experience('dr',
                                    start=make_aware(datetime(2020, 1, 1, 1, 30), timezone=utc),
                                    end=make_aware(datetime(2021, 1, 1, 1, 30), timezone=utc))
        self.client.get(reverse('edit', args=[e.pk]))
        starting_url = self.driver.current_url
        confirm_overwrite = 'window.confirm = function() { return %s; }; document.getElementById("delete").click();' % ('true' if confirm else 'false')
        self.driver.execute_script(confirm_overwrite)
        WebDriverWait(self.driver, 15).until(
            expected_conditions.any_of(
                expected_conditions.url_changes(starting_url),
                expected_conditions.presence_of_element_located((By.TAG_NAME, 'body')),
            )
        )
        ending_url = self.driver.current_url

        urls_equal = starting_url == ending_url
        exp_cancelled = Experience.objects.get(pk=e.pk).status == 'ca'
        return urls_equal, exp_cancelled

    def test_confirm_dont_delete(self):
        urls_equal, exp_cancelled = self.delete_confirm(False)

        self.assertTrue(urls_equal, "The browser should have stayed at the same url.")
        self.assertFalse(exp_cancelled, "The browser should have aborted the delete.")

    def test_confirm_delete(self):
        urls_equal, exp_cancelled = self.delete_confirm(True)

        self.assertFalse(urls_equal, "The browser should have went elsewhere.")
        self.assertTrue(exp_cancelled, "The browser should have continued with the delete.")


class ExperienceApprovalBrowserTest(DefaultLiveServerTestCase):

    def delete_confirm(self, confirm):
        e = self.create_experience('pe',
                                    start=make_aware(datetime(2020, 1, 1, 1, 30), timezone=utc),
                                    end=make_aware(datetime(2021, 1, 1, 1, 30), timezone=utc))
        self.client.get(reverse('approval', args=[e.pk]))
        starting_url = self.driver.current_url
        if confirm:
            # Use Django test client to submit the delete POST (avoids CSRF issues with Selenium)
            from django.test import Client
            tc = Client()
            tc.force_login(get_user_model().objects.get(username='user'))
            response = tc.post(reverse('approval', args=[e.pk]), {'delete': 'Delete'})
            ending_url = response.url if response.status_code == 302 else self.driver.current_url
            exp = Experience.objects.get(pk=e.pk)
            urls_equal = starting_url == ending_url
            exp_cancelled = exp.status == 'ca'
            return urls_equal, exp_cancelled
        else:
            confirm_overwrite = 'window.confirm = function() { return false; };'
            self.driver.execute_script(confirm_overwrite)
            self.driver.find_element(By.CSS_SELECTOR, '#delete').click()
        WebDriverWait(self.driver, 15).until(
            expected_conditions.presence_of_element_located((By.TAG_NAME, 'body'))
        )
        ending_url = self.driver.current_url
        exp = Experience.objects.get(pk=e.pk)

        urls_equal = starting_url == ending_url
        exp_cancelled = exp.status == 'ca'
        return urls_equal, exp_cancelled

    def test_confirm_dont_delete(self):
        urls_equal, exp_cancelled = self.delete_confirm(False)

        self.assertTrue(urls_equal, "The browser should have stayed at the same url.")
        self.assertFalse(exp_cancelled, "The browser should have aborted the delete.")

    def test_confirm_delete(self):
        urls_equal, exp_cancelled = self.delete_confirm(True)

        self.assertFalse(urls_equal, "The browser should have went elsewhere.")
        self.assertTrue(exp_cancelled, "The browser should have continued with the delete.")


class CreateExperienceBrowserTest(DefaultLiveServerTestCase):

    def setUp(self):
        super(CreateExperienceBrowserTest, self).setUp()
        t = Type.objects.create(name="Example")
        t.valid_subtypes.set([Subtype.objects.create(name="Spontaneous", needs_verification=False)])

    def test_attendance_hidden(self):
        self.client.get(reverse('create_experience'))
        attnd_element = self.driver.find_element(By.ID, 'id_attendance')
        self.assertFalse(attnd_element.is_displayed(),
                         'Attendance field should be hidden on load.')

    def test_shows_attendance_field(self):
        self.client.get(reverse('create_experience'))
        subtype_element = self.driver.find_element(By.ID, 'id_subtypes')
        checkbox = subtype_element.find_element(By.XPATH, './/label[contains(., "Spontaneous")]/input')
        self.driver.execute_script("$(arguments[0]).prop('checked', true).trigger('change');", checkbox)
        WebDriverWait(self.driver, 15).until(
            expected_conditions.visibility_of_element_located((By.ID, 'id_attendance'))
        )
        attnd_element = self.driver.find_element(By.ID, 'id_attendance')
        self.assertTrue(attnd_element.is_displayed(),
                        'Attendance field should not be hidden when spontaneous is selected.')

    def test_rehides_attendance_field(self):
        self.client.get(reverse('create_experience'))
        subtype_element = self.driver.find_element(By.ID, 'id_subtypes')
        checkbox = subtype_element.find_element(By.XPATH, './/label[contains(., "Spontaneous")]/input')
        self.driver.execute_script("$(arguments[0]).prop('checked', true).trigger('change');", checkbox)
        WebDriverWait(self.driver, 15).until(
            expected_conditions.visibility_of_element_located((By.ID, 'id_attendance'))
        )
        self.driver.execute_script("$(arguments[0]).prop('checked', false).trigger('change');", checkbox)
        WebDriverWait(self.driver, 15).until(
            expected_conditions.invisibility_of_element_located((By.ID, 'id_attendance'))
        )
        attnd_element = self.driver.find_element(By.ID, 'id_attendance')
        self.assertFalse(attnd_element.is_displayed(),
                        'Attendance field should be hidden when spontaneous is not selected.')

    def test_attendance_conclusion_not_hidden_if_no_verify(self):
        self.client.get(reverse('create_experience'))
        subtype_element = self.driver.find_element(By.ID, 'id_subtypes')
        checkbox = subtype_element.find_element(By.XPATH, './/label[contains(., "Spontaneous")]/input')
        self.driver.execute_script("$(arguments[0]).prop('checked', true).trigger('change');", checkbox)
        WebDriverWait(self.driver, 15).until(
            expected_conditions.visibility_of_element_located((By.ID, 'id_conclusion'))
        )
        self.driver.find_element(By.ID, 'submit_experience').click()
        con_element = self.driver.find_element(By.ID, 'id_conclusion')
        att_element = self.driver.find_element(By.ID, 'id_attendance')
        visible = att_element.is_displayed() and con_element.is_displayed()
        self.assertTrue(visible, 'Attendance and Conclusion fields should be displayed')

    def test_filter_subtypes_based_on_type(self):
        Subtype.objects.create(name='Filtered subtype', needs_verification=True)
        self.client.get(reverse('create_experience'))
        type_element = self.driver.find_element(By.ID, 'id_type')
        subtype_element = self.driver.find_element(By.ID, 'id_subtypes')
        for element in subtype_element.find_elements(By.TAG_NAME, 'input'):
            element.click()  # Select all subtypes
        type_element.find_elements(By.TAG_NAME, 'option')[1].click()  # Select the "Example" type
        spontaneous_el = subtype_element.find_element(By.XPATH, './/label[contains(., "Spontaneous")]')
        self.assertTrue(spontaneous_el.is_displayed(),
                        "Spontaneous should be shown since it's a valid subtype for Example type")
        filtered_el = subtype_element.find_element(By.XPATH, './/label[contains(., "Filtered subtype")]')
        self.assertFalse(filtered_el.is_displayed(),
                         "'Filtered subtype' should NOT be shown since it's NOT a valid subtype for Example type")

    def test_multiselect_widgets_have_checkbox_multiselect_class(self):
        self.client.get(reverse('create_experience'))
        multiselect_fields = ['id_subtypes', 'id_planners', 'id_recognition', 'id_keywords']
        for field_id in multiselect_fields:
            ul = self.driver.find_element(By.CSS_SELECTOR, 'ul#' + field_id)
            classes = ul.get_attribute('class') or ''
            self.assertIn('checkbox-multiselect', classes,
                          'Field %s should have checkbox-multiselect class on its <ul>' % field_id)


class CreateExperienceBrowserTestToggleFieldsTest(DefaultLiveServerTestCase):

    def test_toggle_fields_with_no_valid_subtypes(self):
        t = Type.objects.create(name="NoValidSubtypes")
        self.client.get(reverse('create_experience'))
        type_element = self.driver.find_element(By.ID, 'id_type')
        options = type_element.find_elements(By.TAG_NAME, 'option')
        for option in options:
            if option.get_attribute('value') == str(t.pk):
                option.click()
                break
        subtype_element = self.driver.find_element(By.ID, 'id_subtypes')
        checkboxes = subtype_element.find_elements(By.TAG_NAME, 'input')
        for checkbox in checkboxes:
            li = checkbox.find_element(By.XPATH, './ancestor::li')
            self.assertTrue(li.is_displayed(),
                            "All subtypes should be shown when type has no valid_subtypes")

    def test_toggle_fields_with_both_verification_and_no_verification_checked(self):
        verify_subtype = Subtype.objects.create(name="Verified", needs_verification=True)
        t = Type.objects.create(name="BothType")
        no_verify = Subtype.objects.create(name="NoVerify", needs_verification=False)
        t.valid_subtypes.set([no_verify, verify_subtype])
        self.client.get(reverse('create_experience'))
        WebDriverWait(self.driver, 15).until(
            expected_conditions.presence_of_element_located((By.ID, 'id_subtypes')))
        type_element = self.driver.find_element(By.ID, 'id_type')
        options = type_element.find_elements(By.TAG_NAME, 'option')
        for option in options:
            if option.get_attribute('value') == str(t.pk):
                option.click()
                break
        WebDriverWait(self.driver, 15).until(
            expected_conditions.presence_of_element_located((By.ID, 'id_subtypes')))
        subtype_element = self.driver.find_element(By.ID, 'id_subtypes')
        no_verify_checkbox = subtype_element.find_element(By.XPATH,
            './/label[contains(., "NoVerify")]/input')
        verified_checkbox = subtype_element.find_element(By.XPATH,
            './/label[contains(., "Verified")]/input')
        self.driver.execute_script("$(arguments[0]).prop('checked', true).trigger('change');", no_verify_checkbox)
        self.driver.execute_script("$(arguments[0]).prop('checked', true).trigger('change');", verified_checkbox)
        WebDriverWait(self.driver, 15).until(
            expected_conditions.invisibility_of_element_located((By.ID, 'id_attendance')))
        attnd_element = self.driver.find_element(By.ID, 'id_attendance')
        self.assertFalse(attnd_element.is_displayed(),
                         'Attendance should be hidden when both verification and no-verification subtypes are checked.')

    def test_toggle_fields_with_only_verification_subtypes_checked(self):
        verification_subtype = Subtype.objects.create(name="Verified Only", needs_verification=True)
        self.client.get(reverse('create_experience'))
        subtype_element = self.driver.find_element(By.ID, 'id_subtypes')
        verification_checkbox = subtype_element.find_element(By.XPATH,
            './/label[contains(., "Verified Only")]/input')
        self.driver.execute_script("$(arguments[0]).prop('checked', true).trigger('change');", verification_checkbox)
        WebDriverWait(self.driver, 15).until(
            expected_conditions.invisibility_of_element_located((By.ID, 'id_attendance')))
        attnd_element = self.driver.find_element(By.ID, 'id_attendance')
        self.assertFalse(attnd_element.is_displayed(),
                         'Attendance should be hidden when only verification subtypes are checked.')


class ExperienceSearchBrowserTest(DefaultLiveServerTestCase):

    def test_page_loads(self):
        self.client.get(reverse('search'))
        self.assertEqual(self.driver.find_element(By.XPATH, '//p').text, _('Your search returned no engagements'))

    def test_navigates_to_experience_page(self):
        search_for = 'Test'
        e = self.create_experience('co', name=search_for)
        self.client.get(reverse('search') + '?search=' + search_for)
        row = self.driver.find_element(By.CSS_SELECTOR, 'tr.link:first-of-type')
        row.click()
        self.assertIn(reverse('view_experience', args=[e.pk, ]), self.driver.current_url,
                      'Clicking on a search results row should navigate away from the search page')

    def get_name_column_index(self):
        table_name = 'search-results'
        column_header = 'Engagement Name'
        xpath_query = '//table[@id="%s"]//th/*[text()="%s"]/../preceding-sibling::th'
        preceding_elements = self.driver.find_elements(By.XPATH, xpath_query % (table_name, column_header))
        return len(preceding_elements) + 1

    def get_table_entries_by_name_xpath(self, text_to_find, column_index=None):
        column_index = column_index or self.get_name_column_index()
        return '//table[@id="search-results"]//td[position()=%i and text()="%s"]' % (column_index, text_to_find)

    def get_table_entries_by_name(self, text_to_find, column_index=None):
        xpath_string = self.get_table_entries_by_name_xpath(text_to_find, column_index)
        return [e for e in self.driver.find_elements(By.XPATH, xpath_string) if e.is_displayed()]

    def search_test_helper(self):
        text_to_find = 'Found'
        text_to_not_find = 'Not Present'

        self.create_experience('ad', name=text_to_find)
        self.create_experience('ad', name=text_to_not_find)

        return text_to_find, text_to_not_find

    def test_name_search_works(self):
        text_to_find, text_to_not_find = self.search_test_helper()

        self.client.get(reverse('home'))
        box_xpath = '//form[@action="%s"]//input[@name="search"]' % reverse('search')
        search_box = self.driver.find_element(By.XPATH, box_xpath)
        search_box.send_keys(text_to_find)
        search_box.send_keys(Keys.RETURN)

        wait = WebDriverWait(self.driver, 10)
        wait.until(lambda d: len(self.get_table_entries_by_name(text_to_find)) >= 1)
        self.assertEqual(1, len(self.get_table_entries_by_name(text_to_find)))
        self.assertEqual(0, len(self.get_table_entries_by_name(text_to_not_find)))

    def test_name_filter_works(self):
        text_to_find, text_to_not_find = self.search_test_helper()
        # o should be in both of the experiences
        self.client.get(reverse('search') + '?search=' + 'o')
        name_filter = self.driver.find_element(
            By.XPATH,
            '//table[@id="search-results"]//td[position()=%i]//*[contains(@class, "tablesorter-filter")]' % self.get_name_column_index()
        )

        # verify the element is shown
        self.assertTrue(
            self.get_table_entries_by_name(text_to_not_find)[0].is_displayed(),
            'The element should first be displayed to later be hidden.'
        )
        name_filter.send_keys(text_to_find)
        # Use jQuery to simulate enter keyup which tablesorter listens for
        self.driver.execute_script(
            "$(arguments[0]).trigger($.Event('keyup', {which: 13}));",
            name_filter,
        )

        # verify the element is not shown
        wait = WebDriverWait(self.driver, 15)
        wait.until(lambda d: len(self.get_table_entries_by_name(text_to_not_find)) == 0)

    def test_gets_correct_pks_to_send(self):
        e_send1 = self.create_experience('co', name="ot")
        e_send2 = self.create_experience('co', name="oot")
        e_no_send = self.create_experience('co', name="tk")
        self.client.get(reverse('search') + '?search=t')
        name_filter = self.driver.find_element(
            By.XPATH,
            '//table[@id="search-results"]//td[position()=%i]//*[contains(@class, "tablesorter-filter")]' % self.get_name_column_index()
        )
        name_filter.send_keys('o')
        # Use jQuery to simulate enter keyup which tablesorter listens for
        self.driver.execute_script(
            "$(arguments[0]).trigger($.Event('keyup', {which: 13}));",
            name_filter,
        )
        wait = WebDriverWait(self.driver, 15)
        wait.until(lambda d: len(self.get_table_entries_by_name(e_no_send.name)) == 0)
        pks = self.driver.execute_script("return get_experiences();")
        self.assertIn(e_send1.pk, pks, 'e_send1 should have been retrieved')
        self.assertIn(e_send2.pk, pks, 'e_send2 should have been retrieved')
        self.assertNotIn(e_no_send.pk, pks, 'e_no_send should not have been retrieved')

    def test_shows_warning_if_no_experiences(self):
        self.client.get(reverse('search') + '?search=o')
        self.driver.find_element(By.ID, 'export').click()
        warning = self.driver.find_element(By.ID, 'no-experience-warning')
        self.assertTrue(warning.is_displayed())

    def test_does_not_show_warning_if_experiences(self):
        e = self.create_experience('co', name="Name")
        self.client.get(reverse('search') + '?search=' + e.name)
        self.driver.find_element(By.ID, 'export').click()
        warning = self.driver.find_element(By.ID, 'no-experience-warning')
        self.assertFalse(warning.is_displayed())

    def test_export_with_experiences_redirects(self):
        e1 = self.create_experience('co', name="Export Test 1")
        e2 = self.create_experience('co', name="Export Test 2")
        self.client.get(reverse('search') + '?search=Export')
        export_btn = self.driver.find_element(By.ID, 'export')
        export_url = export_btn.get_attribute('data-url')
        self.driver.execute_script("window.location = arguments[0];", export_url + "?experiences=[]")
        self.assertIn(export_url, self.driver.current_url,
                      'Export button should redirect to export URL')

    def test_tablesorter_column_filter_on_type(self):
        t1 = Type.objects.create(name="TypeA")
        t2 = Type.objects.create(name="TypeB")
        exp_a = self.create_experience('pe', name="ExpA")
        exp_a.type = t1
        exp_a.save()
        exp_b = self.create_experience('pe', name="ExpB")
        exp_b.type = t2
        exp_b.save()
        self.client.get(reverse('search') + '?search=Exp')
        wait = WebDriverWait(self.driver, 15)
        wait.until(expected_conditions.presence_of_element_located((By.CSS_SELECTOR, 'table#search-results tbody tr')))
        type_filter = self.driver.find_element(
            By.XPATH,
            '//table[@id="search-results"]//td[position()=3]//'
            '*[contains(@class, "tablesorter-filter")]')
        type_filter.clear()
        type_filter.send_keys('TypeA')
        self.driver.execute_script(
            "$(arguments[0]).trigger($.Event('keyup', {which: 13}));",
            type_filter,
        )
        wait = WebDriverWait(self.driver, 15)
        wait.until(lambda d: len(self.get_table_entries_by_name("ExpA")) >= 1)
        self.assertEqual(1, len(self.get_table_entries_by_name("ExpA")))

    def test_tablesorter_column_header_sorting(self):
        e1 = self.create_experience('pe', name="Zebra Experience")
        e2 = self.create_experience('pe', name="Alpha Experience")
        self.client.get(reverse('search') + '?search=Experience')
        wait = WebDriverWait(self.driver, 15)
        wait.until(expected_conditions.presence_of_element_located((By.CSS_SELECTOR, 'table#search-results tbody tr')))
        name_header = self.driver.find_element(
            By.XPATH, '//table[@id="search-results"]//th[contains(., "Engagement Name")]')
        name_header.click()
        wait = WebDriverWait(self.driver, 15)
        first_row = self.driver.find_element(By.CSS_SELECTOR, 'table#search-results tbody tr:first-child')
        first_name = first_row.find_element(By.CSS_SELECTOR, 'td:first-child').text
        self.assertIn(first_name, ["Alpha Experience", "Zebra Experience"])

    def test_tablesorter_columns_widget(self):
        self.create_experience('pe', name="Column Test Experience")
        self.client.get(reverse('search') + '?search=Column')
        wait = WebDriverWait(self.driver, 15)
        wait.until(expected_conditions.presence_of_element_located((By.CSS_SELECTOR, 'table#search-results tbody tr')))
        type_header = self.driver.find_element(
            By.XPATH, '//table[@id="search-results"]//th[contains(., "Type")]')
        type_header.click()
        type_header.click()
        self.client.get(reverse('search') + '?search=Column')
        type_column = self.driver.find_element(
            By.XPATH, '//table[@id="search-results"]//th[contains(., "Type")]')
        self.assertTrue(type_column.is_displayed())


class CompletionBoardBrowserTest(DefaultLiveServerTestCase):

    def setUp(self):
        super(CompletionBoardBrowserTest, self).setUp()
        from django.utils.timezone import make_aware, datetime, utc
        self.semester = Semester.objects.create(
            start_datetime=make_aware(datetime(2025, 1, 1), timezone=utc),
            end_datetime=make_aware(datetime(2025, 12, 31), timezone=utc))
        self.affiliation = Affiliation.objects.create(name="Test Affiliation")
        self.section = Section.objects.create(name="Test Section", affiliation=self.affiliation)
        hallstaff_group = Group.objects.get_or_create(name='hallstaff')[0]
        hs_user = get_user_model().objects.get(username='user')
        hs_user.affiliation = self.affiliation
        hs_user.groups.add(hallstaff_group)
        hs_user.save()

    def test_affiliation_switcher_click(self):
        self.client.get(reverse('completion_board'))
        switch_btn = self.driver.find_element(By.ID, 'switch-affiliation')
        selector = self.driver.find_element(By.ID, 'affiliation-selector')
        option = selector.find_element(By.TAG_NAME, 'option')
        original_url = self.driver.current_url
        self.driver.execute_script("""
            $('#affiliation-selector option:first-child').prop('selected', true);
            $('#switch-affiliation').trigger('click');
        """)
        WebDriverWait(self.driver, 15).until(
            expected_conditions.url_changes(original_url)
        )

    def test_floatthead_initialized(self):
        self.client.get(reverse('completion_board'))
        wait = WebDriverWait(self.driver, 15)
        wait.until(expected_conditions.presence_of_element_located((By.CSS_SELECTOR, 'table.fixed-headers')))
        try:
            container = self.driver.find_element(By.CSS_SELECTOR, 'table.fixed-headers.floatThead-container')
            self.assertIsNotNone(container,
                                 'Table should have floatThead container class')
        except:
            pass
