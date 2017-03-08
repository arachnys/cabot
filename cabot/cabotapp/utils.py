from django.contrib.auth import get_user_model


def cabot_needs_setup():
    return not get_user_model().objects.all().exists()
