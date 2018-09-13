from django.db import models


class HipchatInstance(models.Model):
    def __unicode__(self):
        return self.name

    name = models.CharField(
        max_length=20,
        unique=True,
        help_text='Unique name for the Hipchat server.'
    )
    server_url = models.CharField(
        max_length=100,
        help_text='Url for the Hipchat server.'
    )
    api_v2_key = models.CharField(
        max_length=50,
        help_text='API V2 key that will be used for sending alerts.'
    )


class MatterMostInstance(models.Model):
    def __unicode__(self):
        return self.name

    name = models.CharField(
        max_length=20,
        unique=True,
        help_text='Unique name for the Mattermost server.'
    )
    server_url = models.CharField(
        max_length=100,
        help_text='Base url for the Mattermost server.'
    )
    api_token = models.CharField(
        max_length=100,
        help_text='API token that will be used for sending alerts.'
    )
    webhook_url = models.CharField(
        max_length=256,
        help_text='System generated URL for webhook integrations'
    )
    default_channel_id = models.CharField(
        max_length=32,
        help_text='Default channel ID to use if a service does not have one set. '
                  'If blank, services with no channel ID set will log an error when sending alerts.',
        null=True,
        blank=True
    )
