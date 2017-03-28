from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.decorators import login_required
from django.conf import settings


def cabot_login_required(function=None, redirect_field_name=REDIRECT_FIELD_NAME, login_url=settings.LOGIN_URL):
    """
    The login_required() decorator, but disabled if indicated in the settings (for testing).
    """
    if settings.DISABLE_LOGIN:
        return function
    return login_required(function, redirect_field_name, login_url)
