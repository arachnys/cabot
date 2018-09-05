from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Schedule
from .tasks import reset_shifts_and_problems


@receiver(post_save, sender=Schedule, dispatch_uid="reset_shifts_and_problems")
def schedule_post_save(sender, instance, **kwargs):
    reset_shifts_and_problems.apply_async(args=[instance.id])
