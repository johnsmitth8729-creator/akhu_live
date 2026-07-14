from rest_framework import serializers
from regions.models import Region
from cameras.models import Camera, CameraStatus
from logs.models import ActivityLog
from streaming.models import StreamingLog

class RegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = ['id', 'name', 'description', 'logo', 'is_active', 'created_at']


class CameraSerializer(serializers.ModelSerializer):
    region_name = serializers.ReadOnlyField(source='region.name')
    
    class Meta:
        model = Camera
        fields = [
            'id', 'region', 'region_name', 'name', 'description', 'rtsp_url', 
            'ip_address', 'port', 'building', 'floor', 'room', 'status', 'last_seen', 'created_at'
        ]


class CameraStatusSerializer(serializers.ModelSerializer):
    camera_name = serializers.ReadOnlyField(source='camera.name')
    
    class Meta:
        model = CameraStatus
        fields = ['id', 'camera', 'camera_name', 'status', 'response_time', 'error_message', 'checked_at']


class ActivityLogSerializer(serializers.ModelSerializer):
    username = serializers.ReadOnlyField(source='user.username')
    
    class Meta:
        model = ActivityLog
        fields = ['id', 'user', 'username', 'action', 'description', 'ip_address', 'timestamp']


class StreamingLogSerializer(serializers.ModelSerializer):
    camera_name = serializers.ReadOnlyField(source='camera.name')
    
    class Meta:
        model = StreamingLog
        fields = ['id', 'camera', 'camera_name', 'action', 'bandwidth', 'duration', 'timestamp']
