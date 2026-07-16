import uuid
import os
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from regions.models import Region

def recording_upload_path(instance, filename):
    now = timezone.now()
    year = now.strftime('%Y')
    month = now.strftime('%m')
    region_name = instance.live_source.region.name.replace(' ', '_').replace('/', '_')
    date_str = now.strftime('%Y-%m-%d')
    return os.path.join("recordings", year, month, region_name, date_str, filename)


class LiveSource(models.Model):
    class SourceTypes(models.TextChoices):
        IP_CAMERA = 'IP_CAMERA', _('IP Camera')
        SCREEN_SHARE = 'SCREEN_SHARE', _('Desktop Screen')
        WEB_BROWSER = 'WEB_BROWSER', _('Browser Tab')
        WEBCAM = 'WEBCAM', _('Webcam')

    class Statuses(models.TextChoices):
        IDLE = 'idle', _('Idle')
        ONLINE = 'online', _('Online')
        RECORDING = 'recording', _('Recording')
        OFFLINE = 'offline', _('Offline')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    region = models.ForeignKey(
        Region,
        on_delete=models.CASCADE,
        related_name='live_sources',
        verbose_name=_('Region')
    )
    name = models.CharField(max_length=100, verbose_name=_('Source Name'))
    source_type = models.CharField(
        max_length=20,
        choices=SourceTypes.choices,
        verbose_name=_('Source Type')
    )
    status = models.CharField(
        max_length=20,
        choices=Statuses.choices,
        default=Statuses.IDLE,
        verbose_name=_('Status')
    )
    recording_enabled = models.BooleanField(default=False, verbose_name=_('Recording Enabled'))
    streaming_url = models.CharField(max_length=500, blank=True, verbose_name=_('Streaming URL'))
    
    # IP Camera specific parameters
    rtsp_url = models.CharField(max_length=500, blank=True, verbose_name=_('RTSP URL'))
    rtsp_username = models.CharField(max_length=100, blank=True, verbose_name=_('RTSP Username'))
    rtsp_password = models.CharField(max_length=100, blank=True, verbose_name=_('RTSP Password'))
    
    # Location coordinates
    building = models.CharField(max_length=100, blank=True, verbose_name=_('Building'))
    floor = models.CharField(max_length=50, blank=True, verbose_name=_('Floor'))
    room = models.CharField(max_length=50, blank=True, verbose_name=_('Room'))
    
    # Timeline
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))
    last_connected = models.DateTimeField(null=True, blank=True, verbose_name=_('Last Connected'))
    last_disconnected = models.DateTimeField(null=True, blank=True, verbose_name=_('Last Disconnected'))

    class Meta:
        verbose_name = _('Live Source')
        verbose_name_plural = _('Live Sources')
        ordering = ['region', 'source_type', 'name']

    def __str__(self):
        return f"{self.name} ({self.get_source_type_display()}) - {self.region.name}"


class Recording(models.Model):
    live_source = models.ForeignKey(
        LiveSource,
        on_delete=models.CASCADE,
        related_name='recordings',
        verbose_name=_('Live Source')
    )
    file = models.FileField(upload_to=recording_upload_path, verbose_name=_('Recording File'))
    filename = models.CharField(max_length=255, verbose_name=_('Filename'))
    duration = models.IntegerField(default=0, verbose_name=_('Duration (seconds)'))
    filesize = models.BigIntegerField(default=0, verbose_name=_('Filesize (bytes)'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))

    class Meta:
        verbose_name = _('Recording')
        verbose_name_plural = _('Recordings')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.filename} ({self.live_source.name})"


class StreamingNode(models.Model):
    name = models.CharField(max_length=100, verbose_name=_('Node Name'))
    ip_address = models.GenericIPAddressField(verbose_name=_('IP Address'))
    cpu_usage = models.FloatField(default=0.0, verbose_name=_('CPU Usage (%)'))
    ram_usage = models.FloatField(default=0.0, verbose_name=_('RAM Usage (%)'))
    status = models.CharField(
        max_length=20, 
        choices=[('active', _('Active')), ('inactive', _('Inactive'))], 
        default='active', 
        verbose_name=_('Status')
    )
    priority = models.IntegerField(default=1, verbose_name=_('Priority'))

    class Meta:
        verbose_name = _('Streaming Node')
        verbose_name_plural = _('Streaming Nodes')
        ordering = ['priority', '-cpu_usage']

    def __str__(self):
        return f"{self.name} ({self.ip_address})"


class StreamingSetting(models.Model):
    mediamtx_url = models.CharField(max_length=255, default='http://127.0.0.1:9997', verbose_name=_('MediaMTX API URL'))
    mediamtx_webrtc_url = models.CharField(max_length=255, default='http://127.0.0.1:8889', verbose_name=_('MediaMTX WebRTC URL'))
    mediamtx_hls_url = models.CharField(max_length=255, default='http://127.0.0.1:8888', verbose_name=_('MediaMTX HLS URL'))
    mediamtx_playback_url = models.CharField(max_length=255, default='http://127.0.0.1:9996', verbose_name=_('MediaMTX Playback URL'))
    turn_url = models.CharField(max_length=255, default='turn:live.akhu.uz:3478?transport=udp', verbose_name=_('TURN Server URL'))
    stun_url = models.CharField(max_length=255, default='stun:stun.l.google.com:19302', verbose_name=_('STUN Server URL'))
    domain = models.CharField(max_length=100, default='live.akhu.uz', verbose_name=_('Production Domain'))
    https_enabled = models.BooleanField(default=True, verbose_name=_('HTTPS Enabled'))
    recording_enabled = models.BooleanField(default=True, verbose_name=_('Recording Enabled'))
    dvr_buffer_minutes = models.IntegerField(
        default=10,
        verbose_name=_('DVR Buffer (minutes)'),
        help_text=_('Rolling DVR buffer duration in minutes. Default: 10 min. Max: 30 min.')
    )

    class Meta:
        verbose_name = _('Streaming Setting')
        verbose_name_plural = _('Streaming Settings')

    def __str__(self):
        return str(_("System Streaming Settings"))


