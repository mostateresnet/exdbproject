from django.test import TestCase
from django.test.runner import DiscoverRunner
from django.utils.translation import ugettext as _
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.conf import settings
from selenium import webdriver
from selenium.webdriver.common.by import By
import json
import tempfile
import subprocess
import selenium
import copy
import os
import socket
import re

class CustomRunner(DiscoverRunner):
    def __init__(self, *args, **kwargs):
        # running DiscoverRunner constructor for default behavior
        super(self.__class__, self).__init__(*args, **kwargs)

        # deciding which driver to use
        drivers = self.get_drivers()
        browser_arg = kwargs.get('browser')
        if browser_arg:
            global browser_driver
            driver_obj = drivers.get(browser_arg)
            if not driver_obj:
                error = _('Unknown browser %(argument)s\nThe known browsers are: %(browsers)s')
                raise ValueError(error % {'argument' : browser_arg, 'browsers' : ', '.join(drivers.keys())})
        else:
            default_driver = 'phantomjs'
            driver_obj = drivers.get(default_driver)
        self.__class__.browser_driver = lambda : driver_obj.driver(*getattr(driver_obj, 'args', []))

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

        IstanbulCoverage.instrument_istanbul()


    def teardown_test_environment(self, **kwargs):
        IstanbulCoverage.output_coverage(DefaultLiveServerTestCase.running_total.coverage_files)
        super(self.__class__, self).teardown_test_environment(**kwargs)

    def get_drivers(self):
        chrome = lambda : 'chrome'
        chrome.driver = webdriver.Chrome

        edge = lambda : 'edge'
        edge.driver = webdriver.Edge

        firefox = lambda : 'firefox'
        firefox.driver = webdriver.Firefox

        ie = lambda : 'ie'
        ie.driver = webdriver.Ie

        phantomjs = lambda : 'phantomjs'
        phantomjs.driver = webdriver.PhantomJS

        remote = lambda : 'remote'
        remote.driver = webdriver.Remote
        capabilities = {
            'chromeOptions': {
                'androidPackage': 'com.android.chrome',
          }
        }
        remote_webdriver_server = "http://localhost:9515"
        remote.args = ("http://localhost:9515", capabilities)

        return {
            'chrome' : chrome,
            'edge' : edge,
            'firefox' : firefox,
            'ie' : ie,
            'phantomjs' : phantomjs,
            'remote' : remote,
        }

    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument('-b', '--browser')

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
            if type(value) is int:
                result[key] = y[key] + value
            elif type(value) is list:
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
                    self.coverage_files[filename][count_key] = self._combine_count(operand_file_cov[count_key], current_file_cov[count_key])

    def __iadd__(self, operand):
        if type(operand) is dict:
            self._dict_add(operand)
        elif type(operand) == self.__class__:
            self._dict_add(operand.coverage_files)
        else:
            raise TypeError("unsupported operand type(s) for +: '%s' and '%s'" % (self.__class__.__name__, operand.__class__.__name__))
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
        istanbul_process = subprocess.run([
            'istanbul',
            'instrument',
            os.path.join(app_root, 'static'),
            '--output',
            os.path.join(app_root, instrumented_static)])

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
            pass # if __coverage__ doesn't exist ignore it and move on

class SeleniumJSCoverage(DefaultLiveServerTestCase):
    def test_load(self):
        self.driver.get(CustomRunner.live_server_url)
        self.assertEquals(self.driver.find_element(By.XPATH, '//h1').text, _('Welcome'))

    def test_something_else(self):
        self.driver.get(CustomRunner.live_server_url)
        self.assertEquals(self.driver.find_element(By.XPATH, '//h1').text, _('Welcome'))
        self.driver.execute_script('f()')


class WelcomeViewTest(DefaultLiveServerTestCase):
    def test_load(self):
        self.driver.get(CustomRunner.live_server_url)
        self.assertEquals(self.driver.find_element(By.XPATH, '//h1').text, _('Welcome'))

