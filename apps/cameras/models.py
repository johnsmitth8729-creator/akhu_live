from django.db import models
from django.utils.translation import gettext_lazy as _
from regions.models import Region

class Camera(models.Model):
    class Statuses(models.TextChoices):
        ONLINE = 'online', _('Online')
        OFFLINE = 'offline', _('Offline')
        UNKNOWN = 'unknown', _('Unknown')

    region = models.ForeignKey(
        Region,
        on_delete=models.CASCADE,
        related_name='cameras',
        verbose_name=_('Region')
    )
    name = models.CharField(max_length=100, verbose_name=_('Camera Name'))
    description = models.TextField(blank=True, verbose_name=_('Description'))
    rtsp_url = models.CharField(max_length=500, verbose_name=_('RTSP URL'))
    ip_address = models.GenericIPAddressField(verbose_name=_('IP Address'))
    port = models.PositiveIntegerField(default=554, verbose_name=_('Port'))
    username = models.CharField(max_length=100, blank=True, verbose_name=_('Username'))
    password = models.CharField(max_length=100, blank=True, verbose_name=_('Password'))
    building = models.CharField(max_length=100, verbose_name=_('Building'))
    floor = models.CharField(max_length=50, verbose_name=_('Floor'))
    room = models.CharField(max_length=50, verbose_name=_('Room'))
    status = models.CharField(
        max_length=20,
        choices=Statuses.choices,
        default=Statuses.UNKNOWN,
        verbose_name=_('Status')
    )
    last_seen = models.DateTimeField(null=True, blank=True, verbose_name=_('Last Seen'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created Date'))

    class Meta:
        verbose_name = _('Camera')
        verbose_name_plural = _('Cameras')
        ordering = ['region', 'building', 'room', 'name']

    def __str__(self):
        return f"{self.name} ({self.region.name} - {self.room})"


class CameraStatus(models.Model):
    camera = models.ForeignKey(
        Camera,
        on_delete=models.CASCADE,
        related_name='status_checks',
        verbose_name=_('Camera')
    )
    status = models.CharField(
        max_length=20,
        choices=Camera.Statuses.choices,
        verbose_name=_('Status')
    )
    response_time = models.FloatField(null=True, blank=True, verbose_name=_('Response Time (ms)'))
    error_message = models.TextField(null=True, blank=True, verbose_name=_('Error Message'))
    checked_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Checked At'))

    class Meta:
        verbose_name = _('Camera Status')
        verbose_name_plural = _('Camera Statuses')
        ordering = ['-checked_at']
