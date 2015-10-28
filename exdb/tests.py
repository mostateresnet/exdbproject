from django.test import TestCase
from django.test.runner import DiscoverRunner
from django.utils.translation import ugettext as _
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from selenium import webdriver
from selenium.webdriver.common.by import By
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

class WelcomeViewTest(StaticLiveServerTestCase):
    def setUp(self):
        self.driver = CustomRunner.browser_driver()

    def tearDown(self):
        self.driver.quit()

    def test_load(self):
        self.driver.get(CustomRunner.live_server_url)
        self.assertEquals(self.driver.find_element(By.XPATH, '//h1').text, _('Welcome'))

