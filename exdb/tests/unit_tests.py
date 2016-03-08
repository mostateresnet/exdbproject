from django.test import TestCase
from auto_mock import full_mock, easy_mock


class Test(TestCase):

    class ConfigError(Exception):
        pass

    class Http404(Exception):
        pass

    def check_authenticated_user_mocks(self):

        self.resolve = easy_mock('resolve')
        self.resolve.func.view_class.access_level = 'basic'

        settings = easy_mock('settings')
        settings.PERMS_AND_LEVELS = {'basic': lambda user: True}

        stubs = {
            'resolve': lambda path: self.resolve,
            'settings': settings,
            'ConfigError': self.ConfigError,
            'Http404': self.Http404,
        }

        request = easy_mock('request')
        request.path_info = 'some_path'
        request.user.is_superuser = False

        return request, stubs

    def check_authenticated_user_mocker(self, stubs):
        return full_mock('exdb.restricted_access_middleware', 'RestrictedAccess._check_authenticated_user', stubs)

    def test_user_allowed(self):
        request, stubs = self.check_authenticated_user_mocks()
        with self.check_authenticated_user_mocker(stubs) as _check_authenticated_user:
            self.assertIsNone(_check_authenticated_user(request))

    def test_user_insufficient_permissions(self):
        request, stubs = self.check_authenticated_user_mocks()
        stubs['settings'].PERMS_AND_LEVELS['basic'] = lambda user: False
        with self.check_authenticated_user_mocker(stubs) as _check_authenticated_user:
            self.assertRaises(self.Http404, _check_authenticated_user, request)

    def test_access_level_does_not_exist(self):
        request, stubs = self.check_authenticated_user_mocks()
        del stubs['settings'].PERMS_AND_LEVELS['basic']
        with self.check_authenticated_user_mocker(stubs) as _check_authenticated_user:
            self.assertRaises(self.ConfigError, _check_authenticated_user, request)

    def test_access_level_was_not_set(self):
        request, stubs = self.check_authenticated_user_mocks()
        self.resolve.func.view_class.access_level = False
        with self.check_authenticated_user_mocker(stubs) as _check_authenticated_user:
            self.assertRaises(self.ConfigError, _check_authenticated_user, request)

    def test_view_is_not_class_view_and_not_superuser(self):
        request, stubs = self.check_authenticated_user_mocks()
        self.resolve.func.view_class = False
        with self.check_authenticated_user_mocker(stubs) as _check_authenticated_user:
            self.assertRaises(self.Http404, _check_authenticated_user, request)

    def test_view_is_not_class_view_and_is_superuser(self):
        request, stubs = self.check_authenticated_user_mocks()
        self.resolve.func.view_class = False
        request.user.is_superuser = True
        with self.check_authenticated_user_mocker(stubs) as _check_authenticated_user:
            self.assertIsNone(_check_authenticated_user(request))
