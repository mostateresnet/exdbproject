from django.core.checks import Warning, register
from django.conf import settings

@register()
def check_secret_key(app_configs, **kwargs):
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
