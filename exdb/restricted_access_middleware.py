import urllib
import sys
from django.core.urlresolvers import resolve, reverse
from django.http import Http404, HttpResponseRedirect
from django.conf import settings


class ConfigError(Exception):
    pass


class RestrictedAccess(object):
    """
    This middleware manages the security of the exdbproject.
    By ensuring that an unauthenticated user cannot access django pages.
    """

    def _check_authenticated_user(self, request):
        view_function = resolve(request.path_info).func
        view_class = getattr(view_function, 'view_class', False)
        access_level = getattr(view_class, 'access_level', False)

        # if the view isn't class based
        # for now this works to allow access to the admin page
        if view_class is False:
            if request.user.is_superuser:
                return None
            raise Http404('View not in exdb.views and not superuser')

        # if the access_level is not set on the class
        if not access_level:
            raise ConfigError('Access level not set on %s.' % view_class)

        # if the access_level that has been set on the class doesn't exist
        if access_level not in settings.PERMS_AND_LEVELS:
            raise ConfigError('Access level "%s" does not exist.' % access_level)

        # if user has permission, allow
        if settings.PERMS_AND_LEVELS[access_level](request.user):
            return None

        raise Http404('Insufficient permissions')

    def process_request(self, request):
        if request.user.is_authenticated():
            return self._check_authenticated_user(request)
        elif request.path == reverse('login'):
            return None
        else:
            new_path = reverse('login') + '?next=' + urllib.parse.quote(request.get_full_path())
            return HttpResponseRedirect(new_path)
