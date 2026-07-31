import uuid
import os
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from sources.models import LiveSource
from cameras.models import Camera
from regions.models import Region

def recording_thumbnail_path(instance, filename):
    now = timezone.now()
    year = now.strftime('%Y')
    month = now.strftime('%m')
    day = now.strftime('%d')
    region_name = 'default'
    if instance.region:
        region_name = instance.region.name.replace(' ', '_').replace('/', '_')
    elif instance.source and instance.source.region:
        region_name = instance.source.region.name.replace(' ', '_').replace('/', '_')
    return os.path.join("recordings", year, month, day, region_name, "thumbnails", filename)


class LiveSession(models.Model):
    class Statuses(models.TextChoices):
        LIVE = 'live', _('Live Streaming')
        ENDED = 'ended', _('Ended')
        ERROR = 'error', _('Stream Error')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source = models.ForeignKey(
        LiveSource,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='live_sessions',
        verbose_name=_('Live Source')
    )
    camera = models.ForeignKey(
        Camera,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='live_sessions',
        verbose_name=_('Camera')
    )
    region = models.ForeignKey(
        Region,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='live_sessions',
        verbose_name=_('Region')
    )
    stream_id = models.CharField(max_length=100, db_index=True, verbose_name=_('Stream ID'))
    title = models.CharField(max_length=255, default='Live Stream', verbose_name=_('Stream Title'))
    status = models.CharField(
        max_length=20,
        choices=Statuses.choices,
        default=Statuses.LIVE,
        verbose_name=_('Status')
    )
    peak_viewers = models.IntegerField(default=0, verbose_name=_('Peak Viewers'))
    current_viewers = models.IntegerField(default=0, verbose_name=_('Current Viewers'))
    total_views = models.IntegerField(default=0, verbose_name=_('Total Views'))
    resolution = models.CharField(max_length=20, default='1920x1080', verbose_name=_('Resolution'))
    fps = models.IntegerField(default=30, verbose_name=_('FPS'))
    avg_bitrate_kbps = models.IntegerField(default=2500, verbose_name=_('Avg Bitrate (Kbps)'))
    started_at = models.DateTimeField(default=timezone.now, verbose_name=_('Started At'))
    ended_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Ended At'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))

    class Meta:
        verbose_name = _('Live Session')
        verbose_name_plural = _('Live Sessions')
        ordering = ['-started_at']

    def __str__(self):
        return f"{self.title} ({self.stream_id}) - {self.get_status_display()}"

    @property
    def duration_seconds(self):
        if self.ended_at:
            return int((self.ended_at - self.started_at).total_seconds())
        return int((timezone.now() - self.started_at).total_seconds())


class RecordingSession(models.Model):
    class Statuses(models.TextChoices):
        RECORDING = 'recording', _('Recording')
        COMPLETED = 'completed', _('Completed')
        PROCESSING = 'processing', _('Processing')
        FAILED = 'failed', _('Failed')
        ARCHIVED = 'archived', _('Archived')

    class RetentionPolicies(models.TextChoices):
        NEVER = 'never', _('Never Delete')
        DAYS_7 = '7_days', _('Delete after 7 days')
        DAYS_14 = '14_days', _('Delete after 14 days')
        DAYS_30 = '30_days', _('Delete after 30 days')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    live_session = models.OneToOneField(
        LiveSession,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recording_session',
        verbose_name=_('Live Session')
    )
    source = models.ForeignKey(
        LiveSource,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recording_sessions',
        verbose_name=_('Live Source')
    )
    camera = models.ForeignKey(
        Camera,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recording_sessions',
        verbose_name=_('Camera')
    )
    region = models.ForeignKey(
        Region,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recording_sessions',
        verbose_name=_('Region')
    )
    title = models.CharField(max_length=255, default='Live Stream Recording', verbose_name=_('Recording Title'))
    description = models.TextField(blank=True, verbose_name=_('Description'))
    filename = models.CharField(max_length=255, verbose_name=_('Filename'))
    file_path = models.CharField(max_length=500, blank=True, verbose_name=_('File Path'))
    file_url = models.CharField(max_length=500, blank=True, verbose_name=_('File URL'))
    filesize_bytes = models.BigIntegerField(default=0, verbose_name=_('Filesize (bytes)'))
    duration_seconds = models.IntegerField(default=0, verbose_name=_('Duration (seconds)'))
    resolution = models.CharField(max_length=20, default='1080p', verbose_name=_('Resolution'))
    fps = models.IntegerField(default=30, verbose_name=_('FPS'))
    bitrate_kbps = models.IntegerField(default=2500, verbose_name=_('Bitrate (Kbps)'))
    codec = models.CharField(max_length=50, default='h264/aac', verbose_name=_('Codec'))
    thumbnail = models.ImageField(upload_to=recording_thumbnail_path, null=True, blank=True, verbose_name=_('Thumbnail'))
    status = models.CharField(
        max_length=20,
        choices=Statuses.choices,
        default=Statuses.RECORDING,
        verbose_name=_('Status')
    )
    retention_policy = models.CharField(
        max_length=20,
        choices=RetentionPolicies.choices,
        default=RetentionPolicies.NEVER,
        verbose_name=_('Retention Policy')
    )
    started_at = models.DateTimeField(default=timezone.now, verbose_name=_('Started At'))
    ended_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Ended At'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))

    class Meta:
        verbose_name = _('Recording Session')
        verbose_name_plural = _('Recording Sessions')
        ordering = ['-started_at']

    def __str__(self):
        return f"{self.title} ({self.filename}) - {self.get_status_display()}"

    @property
    def filesize_mb(self):
        return round(self.filesize_bytes / (1024 * 1024), 2)

    @property
    def filesize_formatted(self):
        if self.filesize_bytes >= 1073741824:
            return f"{round(self.filesize_bytes / 1073741824, 2)} GB"
        return f"{round(self.filesize_bytes / (1024 * 1024), 1)} MB"

    @property
    def duration_formatted(self):
        mins, secs = divmod(self.duration_seconds, 60)
        hrs, mins = divmod(mins, 60)
        if hrs > 0:
            return f"{hrs:02d}:{mins:02d}:{secs:02d}"
        return f"{mins:02d}:{secs:02d}"


class ViewerEvent(models.Model):
    class EventTypes(models.TextChoices):
        JOIN = 'join', _('Viewer Joined')
        LEAVE = 'leave', _('Viewer Left')
        HEARTBEAT = 'heartbeat', _('Heartbeat')
        SEEK = 'seek', _('Playback Seek')
        QUALITY_CHANGE = 'quality_change', _('Quality Change')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    live_session = models.ForeignKey(
        LiveSession,
        on_delete=models.CASCADE,
        related_name='viewer_events',
        verbose_name=_('Live Session')
    )
    event_type = models.CharField(
        max_length=20,
        choices=EventTypes.choices,
        default=EventTypes.JOIN,
        verbose_name=_('Event Type')
    )
    viewer_ip = models.GenericIPAddressField(null=True, blank=True, verbose_name=_('Viewer IP'))
    user_agent = models.CharField(max_length=255, blank=True, verbose_name=_('User Agent'))
    metadata = models.JSONField(default=dict, blank=True, verbose_name=_('Metadata'))
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name=_('Timestamp'))

    class Meta:
        verbose_name = _('Viewer Event')
        verbose_name_plural = _('Viewer Events')
        ordering = ['-timestamp']


class QualityRendition(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    live_session = models.ForeignKey(
        LiveSession,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='renditions',
        verbose_name=_('Live Session')
    )
    recording_session = models.ForeignKey(
        RecordingSession,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='renditions',
        verbose_name=_('Recording Session')
    )
    label = models.CharField(max_length=20, verbose_name=_('Quality Label'))  # e.g., '1080p', '720p', '480p'
    height = models.IntegerField(default=720, verbose_name=_('Height (px)'))
    width = models.IntegerField(default=1280, verbose_name=_('Width (px)'))
    bitrate_kbps = models.IntegerField(default=2500, verbose_name=_('Bitrate (Kbps)'))
    playlist_url = models.CharField(max_length=500, verbose_name=_('Playlist URL'))
    is_available = models.BooleanField(default=True, verbose_name=_('Is Available'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))

    class Meta:
        verbose_name = _('Quality Rendition')
        verbose_name_plural = _('Quality Renditions')
        ordering = ['-height']

    def __str__(self):
        return f"{self.label} ({self.width}x{self.height} @ {self.bitrate_kbps}Kbps)"


class StoragePolicy(models.Model):
    retention_days = models.IntegerField(default=30, verbose_name=_('Retention Days'))
    auto_cleanup_enabled = models.BooleanField(default=True, verbose_name=_('Auto Cleanup Enabled'))
    max_storage_gb = models.IntegerField(default=500, verbose_name=_('Max Storage Quota (GB)'))
    max_duration_hours = models.IntegerField(default=24, verbose_name=_('Max Recording Duration (Hours)'))
    auto_delete_policy = models.CharField(
        max_length=30,
        choices=[
            ('oldest_first', _('Delete Oldest First')),
            ('warn_only', _('Send Warning Only')),
            ('none', _('Disabled'))
        ],
        default='oldest_first',
        verbose_name=_('Auto Delete Policy')
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated At'))

    class Meta:
        verbose_name = _('Storage Policy')
        verbose_name_plural = _('Storage Policies')

    def __str__(self):
        return f"Storage Policy ({self.retention_days} days / {self.max_storage_gb} GB)"
