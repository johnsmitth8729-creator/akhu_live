from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from cameras.models import Camera
from regions.models import Region
from logs.models import ActivityLog
from logs.middleware import get_current_request_ip, get_current_user

User = get_user_model()

@receiver(user_logged_in)
def log_login(sender, request, user, **kwargs):
    ActivityLog.objects.create(
        user=user,
        action='login',
        description=f"User {user.username} logged in successfully.",
        ip_address=get_current_request_ip()
    )

@receiver(user_logged_out)
def log_logout(sender, request, user, **kwargs):
    if user:
        ActivityLog.objects.create(
            user=user,
            action='logout',
            description=f"User {user.username} logged out.",
            ip_address=get_current_request_ip()
        )

@receiver(user_login_failed)
def log_login_failed(sender, credentials, request, **kwargs):
    username = credentials.get('username', 'Unknown')
    ActivityLog.objects.create(
        user=None,
        action='login_failed',
        description=f"Failed login attempt for username: {username}",
        ip_address=get_current_request_ip()
    )

@receiver(post_save, sender=Camera)
def log_camera_save(sender, instance, created, **kwargs):
    # Determine the triggering user (could be None in system scripts)
    trigger_user = get_current_user()
    action = 'camera_added' if created else 'camera_updated'
    desc = f"Camera '{instance.name}' was added to region '{instance.region.name}'." if created else f"Camera '{instance.name}' in region '{instance.region.name}' was updated."
    ActivityLog.objects.create(
        user=trigger_user,
        action=action,
        description=desc,
        ip_address=get_current_request_ip()
    )

@receiver(post_delete, sender=Camera)
def log_camera_delete(sender, instance, **kwargs):
    ActivityLog.objects.create(
        user=get_current_user(),
        action='camera_removed',
        description=f"Camera '{instance.name}' from region '{instance.region.name}' was deleted.",
        ip_address=get_current_request_ip()
    )

@receiver(post_save, sender=Region)
def log_region_save(sender, instance, created, **kwargs):
    action = 'region_created' if created else 'region_updated'
    desc = f"Region '{instance.name}' was created." if created else f"Region '{instance.name}' was updated (status: {'Active' if instance.is_active else 'Inactive'})."
    ActivityLog.objects.create(
        user=get_current_user(),
        action=action,
        description=desc,
        ip_address=get_current_request_ip()
    )

@receiver(post_delete, sender=Region)
def log_region_delete(sender, instance, **kwargs):
    ActivityLog.objects.create(
        user=get_current_user(),
        action='region_deleted',
        description=f"Region '{instance.name}' was deleted.",
        ip_address=get_current_request_ip()
    )
