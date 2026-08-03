from django.contrib import admin
from sources.models import LiveSource, StreamingNode, StreamingSetting


@admin.register(LiveSource)
class LiveSourceAdmin(admin.ModelAdmin):
    list_display = ('name', 'source_type', 'region', 'status', 'created_at')
    list_filter = ('source_type', 'status', 'region')
    search_fields = ('name', 'building', 'room')


@admin.register(StreamingNode)
class StreamingNodeAdmin(admin.ModelAdmin):
    list_display = ('name', 'ip_address', 'cpu_usage', 'ram_usage', 'status', 'priority')
    list_filter = ('status',)
    search_fields = ('name', 'ip_address')


@admin.register(StreamingSetting)
class StreamingSettingAdmin(admin.ModelAdmin):
    list_display = ('domain', 'mediamtx_url', 'turn_url', 'stun_url', 'https_enabled')
