from django.contrib import admin
from recordings.models import LiveSession, RecordingSession, ViewerEvent, QualityRendition, StoragePolicy

@admin.register(LiveSession)
class LiveSessionAdmin(admin.ModelAdmin):
    list_display = ['title', 'stream_id', 'status', 'peak_viewers', 'current_viewers', 'resolution', 'fps', 'started_at', 'ended_at']
    list_filter = ['status', 'started_at', 'region']
    search_fields = ['title', 'stream_id']


@admin.register(RecordingSession)
class RecordingSessionAdmin(admin.ModelAdmin):
    list_display = ['title', 'filename', 'status', 'retention_policy', 'filesize_formatted', 'duration_formatted', 'started_at']
    list_filter = ['status', 'retention_policy', 'started_at', 'region']
    search_fields = ['title', 'filename']


@admin.register(ViewerEvent)
class ViewerEventAdmin(admin.ModelAdmin):
    list_display = ['live_session', 'event_type', 'viewer_ip', 'timestamp']
    list_filter = ['event_type', 'timestamp']


@admin.register(QualityRendition)
class QualityRenditionAdmin(admin.ModelAdmin):
    list_display = ['label', 'width', 'height', 'bitrate_kbps', 'is_available']


@admin.register(StoragePolicy)
class StoragePolicyAdmin(admin.ModelAdmin):
    list_display = ['retention_days', 'max_storage_gb', 'auto_cleanup_enabled', 'auto_delete_policy', 'updated_at']
