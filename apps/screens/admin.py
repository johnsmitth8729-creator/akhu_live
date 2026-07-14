from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from screens.models import Computer, ScreenSession, ScreenSnapshot, Heartbeat, AgentToken

@admin.register(Computer)
class ComputerAdmin(admin.ModelAdmin):
    list_display = ('name', 'asset_number', 'region', 'building', 'room', 'status', 'last_seen')
    list_filter = ('status', 'region', 'os')
    search_fields = ('name', 'asset_number', 'building', 'room', 'mac_address', 'ip_address')
    readonly_fields = ('agent_id', 'agent_secret_key', 'last_seen')
    fieldsets = (
        (_('Identification'), {
            'fields': ('region', 'name', 'asset_number', 'description')
        }),
        (_('Location'), {
            'fields': ('building', 'floor', 'room', 'department')
        }),
        (_('Agent Authentication'), {
            'fields': ('agent_id', 'agent_secret_key')
        }),
        (_('Live Info & Diagnostics'), {
            'fields': (
                'status', 'last_seen', 'ip_address', 'mac_address', 'hostname', 
                'username', 'os', 'os_version', 'cpu_usage', 'ram_usage', 
                'disk_usage', 'network_speed', 'uptime', 'current_resolution', 
                'current_fps', 'current_bitrate'
            )
        }),
    )


@admin.register(ScreenSession)
class ScreenSessionAdmin(admin.ModelAdmin):
    list_display = ('computer', 'resolution', 'fps', 'bitrate', 'is_active', 'started_at', 'ended_at')
    list_filter = ('is_active', 'started_at')
    search_fields = ('computer__name', 'computer__asset_number')


@admin.register(ScreenSnapshot)
class ScreenSnapshotAdmin(admin.ModelAdmin):
    list_display = ('computer', 'region', 'captured_by', 'captured_at')
    list_filter = ('region', 'captured_at')
    search_fields = ('computer__name', 'captured_by__username')


@admin.register(Heartbeat)
class HeartbeatAdmin(admin.ModelAdmin):
    list_display = ('computer', 'cpu_usage', 'ram_usage', 'disk_usage', 'network_speed', 'uptime', 'timestamp')
    list_filter = ('timestamp',)
    search_fields = ('computer__name',)


@admin.register(AgentToken)
class AgentTokenAdmin(admin.ModelAdmin):
    list_display = ('computer', 'token', 'created_at')
    search_fields = ('computer__name', 'token')
