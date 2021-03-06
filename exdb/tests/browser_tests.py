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
from django.utils.translation import ugettext as _
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.conf import settings
from django.core.urlresolvers import reverse
from django.utils.timezone import datetime, timedelta, now, make_aware, utc

from exdb.models import Experience, Type, Subtype


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
        def chrome(): return 'chrome'  # pylint: disable=multiple-statements
        chrome.driver = webdriver.Chrome

        def edge(): return 'edge'  # pylint: disable=multiple-statements
        edge.driver = webdriver.Edge

        def firefox(): return 'firefox'  # pylint: disable=multiple-statements
        firefox.driver = webdriver.Firefox

        def ie(): return 'ie'  # pylint: disable=multiple-statements
        ie.driver = webdriver.Ie

        def none_obj(): return 'none'  # pylint: disable=multiple-statements
        none_obj.driver = 'none'

        def phantomjs(): return 'phantomjs'  # pylint: disable=multiple-statements
        phantomjs.driver = webdriver.PhantomJS

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

        def __init__(self, driver):
            self.driver = driver
            self.driver.set_window_size(1920, 1080)

        def get(self, url):
            self.driver.get(CustomRunner.live_server_url + url)

        def force_login(self):
            'Login a browser without visiting the login page'
            c = Client()
            # avoid setting the password and force_login for speed
            user_object = get_user_model().objects.create(username='user', first_name="User")
            c.force_login(user_object)
            if CustomRunner.live_server_url not in self.driver.current_url:
                # if we would be trying to set a cross domain cookie change the domain
                self.get(reverse('login'))

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
        d = self.driver.find_element(By.CSS_SELECTOR, '#delete')
        confirm_overwrite = 'window.confirm = function() { return %s; }' % ('true' if confirm else 'false')
        self.driver.execute_script(confirm_overwrite)
        d.click()
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
        d = self.driver.find_element(By.CSS_SELECTOR, '#delete')
        confirm_overwrite = 'window.confirm = function() { return %s; }' % ('true' if confirm else 'false')
        self.driver.execute_script(confirm_overwrite)
        d.click()
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


class CreateExperienceBrowserTest(DefaultLiveServerTestCase):

    def setUp(self):
        super(CreateExperienceBrowserTest, self).setUp()
        t = Type.objects.create(name="Example")
        t.valid_subtypes = [Subtype.objects.create(name="Spontaneous", needs_verification=False)]

    def test_attendance_hidden(self):
        self.client.get(reverse('create_experience'))
        attnd_element = self.driver.find_element(By.ID, 'id_attendance')
        self.assertFalse(attnd_element.is_displayed(),
                         'Attendance field should be hidden on load.')

    def test_shows_attendance_field(self):
        self.client.get(reverse('create_experience'))
        subtype_element = self.driver.find_element(By.ID, 'id_subtypes')
        subtype_element.find_element_by_class_name('no-verification').click()
        attnd_element = self.driver.find_element(By.ID, 'id_attendance')
        self.assertTrue(attnd_element.is_displayed(),
                        'Attendance field should not be hidden when spontaneous is selected.')

    def test_rehides_attendance_field(self):
        self.client.get(reverse('create_experience'))
        subtype_element = self.driver.find_element(By.ID, 'id_subtypes')
        subtype_element.find_element_by_class_name('no-verification').click()
        subtype_element.find_element_by_class_name('no-verification').click()
        attnd_element = self.driver.find_element(By.ID, 'id_attendance')
        self.assertFalse(attnd_element.is_displayed(),
                         'Attendance field should be hidden when spontaneous is not selected.')

    def test_attendance_conclusion_not_hidden_if_no_verify(self):
        self.client.get(reverse('create_experience'))
        subtype_element = self.driver.find_element(By.ID, 'id_subtypes')
        subtype_element.find_element_by_class_name('no-verification').click()
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
        for element in subtype_element.find_elements_by_tag_name('input'):
            element.click()  # Select all subtypes
        type_element.find_elements_by_tag_name('option')[1].click()  # Select the "Example" type
        self.assertTrue(subtype_element.find_element_by_class_name('no-verification').is_displayed(),
                        "Spontaneous should be shown since it's a valid subtype for Example type")
        self.assertFalse(subtype_element.find_element_by_class_name('verification').is_displayed(),
                         "'Filtered subtype' should NOT be shown since it's NOT a valid subtype for Example type")


class ExperienceSearchBrowserTest(DefaultLiveServerTestCase):

    def test_page_loads(self):
        self.client.get(reverse('search'))
        self.assertEqual(self.driver.find_element(By.XPATH, '//p').text, _('Your search returned no experiences'))

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
        column_header = 'Experience Name'
        xpath_query = '//table[@id="%s"]//th/*[text()="%s"]/../preceding-sibling::th'
        preceding_elements = self.driver.find_elements(By.XPATH, xpath_query % (table_name, column_header))
        return len(preceding_elements) + 1

    def get_table_entries_by_name_xpath(self, text_to_find, column_index=None):
        column_index = column_index or self.get_name_column_index()
        return '//table[@id="search-results"]//td[position()=%i and text()="%s"]' % (column_index, text_to_find)

    def get_table_entries_by_name(self, text_to_find, column_index=None):
        xpath_string = self.get_table_entries_by_name_xpath(text_to_find, column_index)
        return self.driver.find_elements(By.XPATH, xpath_string)

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

        # this test should be safe to use on page load even though there is a race condition
        # due to the careful structure of the search
        # if it fails randomly start checking here
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
        name_filter.send_keys(Keys.RETURN)

        # verify the element is not shown
        wait = WebDriverWait(self.driver, 1)
        wait.until(
            expected_conditions.invisibility_of_element_located(
                (By.XPATH, self.get_table_entries_by_name_xpath(text_to_not_find))
            )
        )
        self.assertFalse(
            self.get_table_entries_by_name(text_to_not_find)[0].is_displayed(),
            'The element should not be visible.'
        )

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
        name_filter.send_keys(Keys.RETURN)
        wait = WebDriverWait(self.driver, 1)
        wait.until(
            expected_conditions.invisibility_of_element_located(
                (By.XPATH, self.get_table_entries_by_name_xpath(e_no_send.name))
            )
        )
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
