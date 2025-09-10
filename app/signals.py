from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver

from app.logwatcher import log_manager
from app.models import LogFile


@receiver(pre_save, sender=LogFile)
def logfile_pre_save(sender, instance, **kwargs):
    """Detect path changes before save so we can clean up the old watcher."""
    if not instance.pk:
        return  # new object, nothing to compare yet

    try:
        old_instance = LogFile.objects.get(pk=instance.pk)
    except LogFile.DoesNotExist:
        return

    if old_instance.path != instance.path:
        # Stop watcher on the old path
        log_manager.stop_watcher(old_instance)


@receiver(post_save, sender=LogFile)
def logfile_post_save(sender, instance, created, **kwargs):
    """Ensure watcher is started (new or updated)."""
    log_manager.start_watcher(instance)


@receiver(post_delete, sender=LogFile)
def logfile_deleted(sender, instance, **kwargs):
    """Clean up watcher when a LogFile is deleted."""
    log_manager.stop_watcher(instance)