from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from app.logwatcher import log_manager
from app.models import LogFile


@receiver(post_save, sender=LogFile)
def log_file_save(sender, instance, **kwargs):
    log_manager.refresh()


@receiver(post_delete, sender=LogFile)
def log_file_delete(sender, instance, **kwargs):
    log_manager.refresh()