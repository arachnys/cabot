from django.conf import settings
from django.db import models
from django.db.models.signals import post_save

class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, related_name='profile')

    def user_data(self):

        from cabot.cabotapp.admin import AlertPluginUserData;

        for user_data_subclass in AlertPluginUserData.__subclasses__():
            user_data = user_data_subclass.objects.get_or_create(user=self, title=user_data_subclass.name)
        return AlertPluginUserData.objects.filter(user=self)

    def __unicode__(self):
        return 'User profile: %s' % self.user.username

    def save(self, *args, **kwargs):
        # Enforce uniqueness
        if self.fallback_alert_user:
            profiles = UserProfile.objects.exclude(id=self.id)
            profiles.update(fallback_alert_user=False)
        return super(UserProfile, self).save(*args, **kwargs)

    @property
    def prefixed_mobile_number(self):
        return '+%s' % self.mobile_number

    mobile_number = models.CharField(max_length=20, blank=True, default='')
    hipchat_alias = models.CharField(max_length=50, blank=True, default='')
    fallback_alert_user = models.BooleanField(default=False)

def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

post_save.connect(create_user_profile, sender=settings.AUTH_USER_MODEL)

def get_duty_officers(at_time=None):
    """Returns a list of duty officers for a given time or now if none given"""
    duty_officers = []
    if not at_time:
        at_time = timezone.now()
    current_shifts = Shift.objects.filter(
        deleted=False,
        start__lt=at_time,
        end__gt=at_time,
    )
    if current_shifts:
        duty_officers = [shift.user for shift in current_shifts]
        return duty_officers
    else:
        try:
            u = UserProfile.objects.get(fallback_alert_user=True)
            return [u.user]
        except UserProfile.DoesNotExist:
            return []
