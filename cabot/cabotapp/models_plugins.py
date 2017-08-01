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
