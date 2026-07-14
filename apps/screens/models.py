import uuid
import secrets
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from regions.models import Region

class Computer(models.Model):
    class Statuses(models.TextChoices):
        OFFLINE = 'offline', _('Offline')
        ONLINE = 'online', _('Online')
        STREAMING = 'streaming', _('Streaming')
        DISCONNECTED = 'disconnected', _('Disconnected')

    region = models.ForeignKey(
        Region,
        on_delete=models.CASCADE,
        related_name='computers',
        verbose_name=_('Region')
    )
    name = models.CharField(max_length=100, verbose_name=_('Computer Name'))
    asset_number = models.CharField(max_length=100, unique=True, verbose_name=_('Asset Number'))
    os = models.CharField(max_length=100, verbose_name=_('Operating System'))
    department = models.CharField(max_length=100, verbose_name=_('Department'))
    building = models.CharField(max_length=100, verbose_name=_('Building'))
    floor = models.CharField(max_length=50, verbose_name=_('Floor'))
    room = models.CharField(max_length=50, verbose_name=_('Room'))
    description = models.TextField(blank=True, verbose_name=_('Description'))
    
    # Agent credentials
    agent_id = models.UUIDField(default=uuid.uuid4, unique=True, verbose_name=_('Agent ID'))
    agent_secret_key = models.CharField(max_length=256, blank=True, verbose_name=_('Agent Secret Key'))
    
    # Live Status
    status = models.CharField(
        max_length=20,
        choices=Statuses.choices,
        default=Statuses.OFFLINE,
        verbose_name=_('Status')
    )
    last_seen = models.DateTimeField(null=True, blank=True, verbose_name=_('Last Seen'))
    
    # Real-time metrics
    current_resolution = models.CharField(max_length=50, blank=True, verbose_name=_('Current Resolution'))
    current_fps = models.IntegerField(default=0, verbose_name=_('Current FPS'))
    current_bitrate = models.FloatField(default=0.0, verbose_name=_('Current Bitrate (Kbps)'))
    
    # System Information
    hostname = models.CharField(max_length=100, blank=True, verbose_name=_('Hostname'))
    username = models.CharField(max_length=100, blank=True, verbose_name=_('Username'))
    os_version = models.CharField(max_length=150, blank=True, verbose_name=_('OS Version'))
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name=_('IP Address'))
    mac_address = models.CharField(max_length=50, blank=True, verbose_name=_('MAC Address'))
    cpu_usage = models.FloatField(default=0.0, verbose_name=_('CPU Usage (%)'))
    ram_usage = models.FloatField(default=0.0, verbose_name=_('RAM Usage (%)'))
    disk_usage = models.FloatField(default=0.0, verbose_name=_('Disk Usage (%)'))
    network_speed = models.FloatField(default=0.0, verbose_name=_('Network Speed (Mbps)'))
    uptime = models.FloatField(default=0.0, verbose_name=_('Uptime (Hours)'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created Date'))

    class Meta:
        verbose_name = _('Computer')
        verbose_name_plural = _('Computers')
        ordering = ['region', 'building', 'room', 'name']

    def __str__(self):
        return f"{self.name} - {self.asset_number} ({self.region.name})"

    def save(self, *args, **kwargs):
        if not self.agent_secret_key:
            self.agent_secret_key = secrets.token_hex(32)
        super().save(*args, **kwargs)


class ScreenSession(models.Model):
    computer = models.ForeignKey(
        Computer,
        on_delete=models.CASCADE,
        related_name='screen_sessions',
        verbose_name=_('Computer')
    )
    resolution = models.CharField(max_length=50, verbose_name=_('Resolution'))
    fps = models.IntegerField(verbose_name=_('FPS'))
    bitrate = models.FloatField(verbose_name=_('Bitrate (Kbps)'))
    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))
    started_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Started At'))
    ended_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Ended At'))

    class Meta:
        verbose_name = _('Screen Session')
        verbose_name_plural = _('Screen Sessions')
        ordering = ['-started_at']


class ScreenSnapshot(models.Model):
    screenshot = models.ImageField(upload_to='screenshots/', verbose_name=_('Screenshot'))
    computer = models.ForeignKey(
        Computer,
        on_delete=models.CASCADE,
        related_name='snapshots',
        verbose_name=_('Computer')
    )
    region = models.ForeignKey(
        Region,
        on_delete=models.CASCADE,
        related_name='screen_snapshots',
        verbose_name=_('Region')
    )
    captured_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('Captured By')
    )
    captured_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Captured At'))

    class Meta:
        verbose_name = _('Screen Snapshot')
        verbose_name_plural = _('Screen Snapshots')
        ordering = ['-captured_at']


class Heartbeat(models.Model):
    computer = models.ForeignKey(
        Computer,
        on_delete=models.CASCADE,
        related_name='heartbeats',
        verbose_name=_('Computer')
    )
    cpu_usage = models.FloatField(verbose_name=_('CPU Usage (%)'))
    ram_usage = models.FloatField(verbose_name=_('RAM Usage (%)'))
    disk_usage = models.FloatField(verbose_name=_('Disk Usage (%)'))
    network_speed = models.FloatField(verbose_name=_('Network Speed (Mbps)'))
    uptime = models.FloatField(verbose_name=_('Uptime (Hours)'))
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name=_('Timestamp'))

    class Meta:
        verbose_name = _('Heartbeat')
        verbose_name_plural = _('Heartbeats')
        ordering = ['-timestamp']


class AgentToken(models.Model):
    computer = models.OneToOneField(
        Computer,
        on_delete=models.CASCADE,
        related_name='auth_token',
        verbose_name=_('Computer')
    )
    token = models.CharField(max_length=64, unique=True, verbose_name=_('Token'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))

    class Meta:
        verbose_name = _('Agent Token')
        verbose_name_plural = _('Agent Tokens')

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_hex(32)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Token for {self.computer.name}"
