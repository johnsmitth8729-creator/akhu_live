from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, TemplateView, View
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from screens.models import Computer, ScreenSession, ScreenSnapshot, Heartbeat, AgentToken
from screens.forms import ComputerForm

class ComputerQuerysetMixin(LoginRequiredMixin):
    """
    Mixin restricting computer model queries to the logged-in user's region (unless Super Admin).
    """
    def get_queryset(self):
        user = self.request.user
        if user.is_super_admin():
            return Computer.objects.all()
        elif user.is_region_admin() and hasattr(user, 'region'):
            return Computer.objects.filter(region=user.region)
        return Computer.objects.none()






class ComputerDiagnosticsAPIView(ComputerQuerysetMixin, View):
    def get(self, request, *args, **kwargs):
        from django.http import JsonResponse
        from django.core.cache import cache
        import requests
        from django.utils import timezone
        
        computer = get_object_or_404(Computer, id=self.kwargs.get('pk'))
        stream_name = f"screen_{computer.id}"
        
        # 1. Registration & Token Status
        try:
            token = computer.auth_token.token
            token_valid = True
        except Exception:
            token = "NOT FOUND"
            token_valid = False
            
        # 2. Activity / Registration log
        from logs.models import ActivityLog
        registration_log = ActivityLog.objects.filter(
            action='agent_registered',
            description__icontains=computer.name
        ).first()
        
        reg_time = registration_log.created_at.strftime('%Y-%m-%d %H:%M:%S') if registration_log else "Never"
        
        # 3. MediaMTX active path info
        api_url = getattr(settings, 'MEDIAMTX_API_URL', 'http://192.168.1.231:9997')
        mediamtx_online = False
        publishing_active = False
        publisher_details = None
        reader_count = 0
        
        try:
            res = requests.get(f"{api_url}/v3/paths/list", timeout=1.5)
            if res.status_code == 200:
                mediamtx_online = True
                items = res.json().get('items', {})
                if stream_name in items:
                    path_data = items[stream_name]
                    publishing_active = path_data.get('source') is not None
                    reader_count = len(path_data.get('readers', []))
                    publisher_details = path_data.get('source')
        except Exception as e:
            pass
            
        # 4. FFmpeg diagnostics from cache
        cache_data = cache.get(f"ffmpeg_diagnostics_{computer.id}", {})
        ffmpeg_cmd = cache_data.get('command', 'FFmpeg not launched yet')
        ffmpeg_stderr = cache_data.get('stderr', 'No logs received from agent yet')
        last_log_time = cache_data.get('updated_at', None)
        
        # 5. Connected calculation
        is_agent_connected = False
        if computer.last_seen:
            diff = (timezone.now() - computer.last_seen).total_seconds()
            if diff < 30: # active heartbeat within 30 seconds
                is_agent_connected = True

        data = {
            "status": computer.status,
            "last_seen_str": computer.last_seen.strftime('%Y-%m-%d %H:%M:%S') if computer.last_seen else "Never",
            "is_agent_connected": is_agent_connected,
            "registration": {
                "token": token,
                "token_valid": token_valid,
                "registered_at": reg_time
            },
            "mediamtx": {
                "api_online": mediamtx_online,
                "publishing_active": publishing_active,
                "reader_count": reader_count,
                "publisher_details": publisher_details
            },
            "ffmpeg": {
                "command": ffmpeg_cmd,
                "stderr": ffmpeg_stderr,
                "updated_at": last_log_time
            },
            "metrics": {
                "cpu_usage": computer.cpu_usage,
                "ram_usage": computer.ram_usage,
                "disk_usage": computer.disk_usage,
                "ip_address": computer.ip_address,
                "mac_address": computer.mac_address,
                "hostname": computer.hostname,
                "username": computer.username,
                "uptime": computer.uptime
            }
        }
        return JsonResponse(data)
