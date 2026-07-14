from django.db import models
from django.utils.translation import gettext_lazy as _
from cameras.models import Camera

class StreamingLog(models.Model):
    class Actions(models.TextChoices):
        STARTED = 'started', _('Stream Started')
        STOPPED = 'stopped', _('Stream Stopped')

    camera = models.ForeignKey(
        Camera,
        on_delete=models.CASCADE,
        related_name='streaming_logs',
        verbose_name=_('Camera')
    )
    action = models.CharField(
        max_length=20,
        choices=Actions.choices,
        verbose_name=_('Action')
    )
    bandwidth = models.FloatField(null=True, blank=True, verbose_name=_('Bandwidth (Mbps)'))
    duration = models.DurationField(null=True, blank=True, verbose_name=_('Duration'))
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name=_('Timestamp'))

    class Meta:
        verbose_name = _('Streaming Log')
        verbose_name_plural = _('Streaming Logs')
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.camera.name} - {self.action} at {self.timestamp}"
