from rest_framework import serializers
from screens.models import Computer, ScreenSession, ScreenSnapshot, Heartbeat

class ComputerSerializer(serializers.ModelSerializer):
    region_name = serializers.ReadOnlyField(source='region.name')
    
    class Meta:
        model = Computer
        fields = [
            'id', 'region', 'region_name', 'name', 'asset_number', 'os', 
            'department', 'building', 'floor', 'room', 'description', 
            'agent_id', 'status', 'last_seen', 'current_resolution', 
            'current_fps', 'current_bitrate', 'hostname', 'username', 
            'os_version', 'ip_address', 'mac_address', 'cpu_usage', 
            'ram_usage', 'disk_usage', 'network_speed', 'uptime', 'created_at'
        ]
        read_only_fields = ['agent_id', 'status', 'last_seen']


class ScreenSnapshotSerializer(serializers.ModelSerializer):
    computer_name = serializers.ReadOnlyField(source='computer.name')
    region_name = serializers.ReadOnlyField(source='region.name')
    captured_by_name = serializers.ReadOnlyField(source='captured_by.username')
    
    class Meta:
        model = ScreenSnapshot
        fields = [
            'id', 'screenshot', 'computer', 'computer_name', 'region', 
            'region_name', 'captured_by', 'captured_by_name', 'captured_at'
        ]
