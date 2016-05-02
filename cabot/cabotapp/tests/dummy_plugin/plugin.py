#
# Example plugins for testing cabot
#

from cabot.plugins.models import AlertPlugin, StatusCheckPlugin
from django import forms

# Example Alert Plugin

class ChatMessengerUserSettingsForm(forms.Form):
    nickname = forms.CharField(max_length=64)

class ChatMessengerAlertPlugin(AlertPlugin):
    name = "Chat Messenger"
    slug = "chat_messenger_alert"
    author = "Jonathan Balls"
    version = "0.0.1"
    font_icon = "fa fa-cog"

    plugin_variables = [
        'PLUGIN_ROOM',
        'PLUGIN_API_KEY'
    ]

    user_config_form = ChatMessengerUserSettingsForm

    def send_alert(self, service, users, duty_officers):
        "A real plugin would implement this."
        pass


# Example Check Plugin

class PortOpenStatusCheckForm(forms.Form):
    port = forms.IntegerField(min_value=0, max_value=65535)
    address = forms.CharField()


class PortOpenStatusCheckPlugin(StatusCheckPlugin):
    name = "Port Open"
    slug = "port_open_check"
    author = "Jonathan Balls"
    version = "0.0.1"
    font_icon = "glyphicon glyphicon-transfer"

    config_form = PortOpenStatusCheckForm

    def run(self, check, result):
        "A real plugin would implement this."
        result.succeeded = False
        return result

    def description(self, check):
        return 'Testing Port {}'.format(check.get_attribute('port'))

