from rest_framework import serializers
from recordings.models import RecordingSession, LiveSession, StoragePolicy, QualityRendition

class QualityRenditionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QualityRendition
        fields = ['id', 'label', 'height', 'width', 'bitrate_kbps', 'playlist_url', 'is_available']


class LiveSessionSerializer(serializers.ModelSerializer):
    duration_seconds = serializers.ReadOnlyField()

    class Meta:
        model = LiveSession
        fields = ['id', 'stream_id', 'title', 'status', 'peak_viewers', 'current_viewers', 'total_views', 'resolution', 'fps', 'started_at', 'ended_at', 'duration_seconds']


class RecordingSessionSerializer(serializers.ModelSerializer):
    filesize_formatted = serializers.ReadOnlyField()
    duration_formatted = serializers.ReadOnlyField()
    region_name = serializers.SerializerMethodField()
    source_name = serializers.SerializerMethodField()

    class Meta:
        model = RecordingSession
        fields = [
            'id', 'title', 'description', 'filename', 'file_path', 'file_url',
            'filesize_bytes', 'filesize_formatted', 'duration_seconds', 'duration_formatted',
            'resolution', 'fps', 'bitrate_kbps', 'codec', 'thumbnail', 'status', 'retention_policy',
            'region_name', 'source_name', 'started_at', 'ended_at', 'created_at'
        ]

    def get_region_name(self, obj):
        return obj.region.name if obj.region else 'N/A'

    def get_source_name(self, obj):
        if obj.source:
            return obj.source.name
        elif obj.camera:
            return obj.camera.name
        return 'N/A'


class StoragePolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = StoragePolicy
        fields = ['retention_days', 'auto_cleanup_enabled', 'max_storage_gb', 'max_duration_hours', 'auto_delete_policy', 'updated_at']
