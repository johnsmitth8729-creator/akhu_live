from rest_framework import serializers
from sources.models import LiveSource


class LiveSourceSerializer(serializers.ModelSerializer):
    region_name = serializers.ReadOnlyField(source='region.name')
    source_type_display = serializers.ReadOnlyField(source='get_source_type_display')
    status_display = serializers.ReadOnlyField(source='get_status_display')

    class Meta:
        model = LiveSource
        fields = [
            'id', 'region', 'region_name', 'name', 'source_type', 'source_type_display',
            'status', 'status_display', 'streaming_url',
            'rtsp_url', 'rtsp_username', 'rtsp_password', 'building', 'floor', 'room',
            'created_at', 'updated_at', 'last_connected', 'last_disconnected',
        ]
        read_only_fields = ['status', 'created_at', 'updated_at', 'last_connected', 'last_disconnected']
