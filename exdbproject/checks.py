from django.core.checks import Warning, Error, register  # pylint: disable=redefined-builtin
from django.conf import settings


@register()
def check_secret_key(**kwargs):
    errors = []
    if settings.BAD_SECRET_KEY == settings.SECRET_KEY:
        errors.append(
            Warning(
                'SECRET_KEY is insecure',
                hint='Generate a secure SECRET_KEY and place it in settings_local.py',
                obj=settings,
                id='exdb.W001'
            )
        )
    return errors


@register()
def check_restricted_access(**kwargs):
    errors = []
    if settings.RESTRICTED_ACCESS_MIDDLEWARE not in settings.MIDDLEWARE_CLASSES:
        errors.append(
            Error(
                'Access is not restricted',
                hint='Make sure that the restricted access middleware is installed.',
                obj=settings,
                id='exdb.E001'
            )
        )
    return errors
