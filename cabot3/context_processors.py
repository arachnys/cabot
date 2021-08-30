from django.conf import settings


def global_settings(request):
    return {
        'ENABLE_SUBSCRIPTION': settings.ENABLE_SUBSCRIPTION,
        'ENABLE_DUTY_ROTA': settings.ENABLE_DUTY_ROTA,
    }
