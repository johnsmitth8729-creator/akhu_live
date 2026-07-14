import shutil
from django.shortcuts import render, redirect
from django.views.generic import TemplateView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.urls import reverse
from core.permissions import SuperAdminRequiredMixin, RegionAdminRequiredMixin
from regions.models import Region
from cameras.models import Camera, CameraStatus
from logs.models import ActivityLog
from streaming.models import StreamingLog
from streaming.services import MediaMTXService
from sources.models import LiveSource, Recording, StreamingSetting

class HomeView(TemplateView):
    """
    Public Home Page displaying all regions and active cameras + live sources in a grid.
    Includes region, building, and status filters.
    """
    template_name = 'dashboard/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Pull filters
        region_id = self.request.GET.get('region', '')
        building = self.request.GET.get('building', '')
        status = self.request.GET.get('status', '')
        search_query = self.request.GET.get('search', '')

        # Build camera and source querysets
        cameras = Camera.objects.select_related('region').filter(region__is_active=True)
        live_sources = LiveSource.objects.select_related('region').filter(region__is_active=True)

        if region_id:
            cameras = cameras.filter(region_id=region_id)
            live_sources = live_sources.filter(region_id=region_id)
        if building:
            cameras = cameras.filter(building__icontains=building)
            live_sources = live_sources.filter(building__icontains=building)
        if status:
            if status == 'online':
                cameras = cameras.filter(status=Camera.Statuses.ONLINE)
                live_sources = live_sources.filter(status__in=[LiveSource.Statuses.ONLINE, LiveSource.Statuses.RECORDING])
            elif status == 'offline':
                cameras = cameras.filter(status=Camera.Statuses.OFFLINE)
                live_sources = live_sources.filter(status__in=[LiveSource.Statuses.OFFLINE, LiveSource.Statuses.IDLE])
        if search_query:
            cameras = cameras.filter(name__icontains=search_query) | \
                      cameras.filter(room__icontains=search_query) | \
                      cameras.filter(building__icontains=search_query)
            live_sources = live_sources.filter(name__icontains=search_query) | \
                           live_sources.filter(room__icontains=search_query) | \
                           live_sources.filter(building__icontains=search_query)

        # Get unique buildings list for the filter select
        camera_buildings = list(Camera.objects.values_list('building', flat=True).distinct())
        source_buildings = list(LiveSource.objects.values_list('building', flat=True).distinct())
        context['buildings'] = sorted(list(set(filter(None, camera_buildings + source_buildings))))
        
        # Group cameras and live sources by region
        regions_list = Region.objects.filter(is_active=True)
        region_streams = {}
        
        request_host = self.request.get_host().split(':')[0]
        
        def get_dynamic_url(url_str):
            if not url_str:
                return url_str
            if '127.0.0.1' in url_str or 'localhost' in url_str:
                return url_str.replace('127.0.0.1', request_host).replace('localhost', request_host)
            return url_str

        db_settings = StreamingSetting.objects.first()
        if db_settings:
            hls_base = get_dynamic_url(db_settings.mediamtx_hls_url)
            webrtc_base = get_dynamic_url(db_settings.mediamtx_webrtc_url)
            stun_url = db_settings.stun_url
            turn_url = db_settings.turn_url
        else:
            hls_base = get_dynamic_url(getattr(settings, 'MEDIAMTX_HLS_URL', 'http://127.0.0.1:8888'))
            webrtc_base = get_dynamic_url(getattr(settings, 'MEDIAMTX_WEBRTC_URL', 'http://127.0.0.1:8889'))
            stun_url = 'stun:stun.l.google.com:19302'
            turn_url = 'turn:live.akhu.uz:3478?transport=udp'

        context['stun_url'] = stun_url
        context['turn_url'] = turn_url

        for r in regions_list:
            streams = []
            
            # Group cameras
            rcams = [c for c in cameras if c.region_id == r.id]
            for c in rcams:
                c_urls = MediaMTXService.get_stream_urls(c)
                c_urls = {k: get_dynamic_url(v) for k, v in c_urls.items()}
                streams.append({
                    'unique_id': f"camera_{c.id}",
                    'id': c.id,
                    'name': c.name,
                    'status': c.status,
                    'is_online': c.status == Camera.Statuses.ONLINE,
                    'is_recording': False,
                    'building': c.building,
                    'room': c.room,
                    'floor': c.floor,
                    'source_type_label': _('IP Camera'),
                    'stream_urls': c_urls,
                    'is_camera': True,
                    'check_status_url': reverse('cameras:check_status', args=[c.id])
                })
                
            # Group live sources
            rsources = [s for s in live_sources if s.region_id == r.id]
            for s in rsources:
                s_urls = {
                    "hls": f"{hls_base}/source_{s.id}/index.m3u8",
                    "webrtc": f"{webrtc_base}/source_{s.id}/",
                    "whep": f"{webrtc_base}/source_{s.id}/whep",
                }
                # Super Admin/Viewers must see everything simply as 'LIVE'
                source_type_label = _('LIVE')
                streams.append({
                    'unique_id': f"source_{s.id}",
                    'id': str(s.id),
                    'name': s.name,
                    'status': s.status,
                    'is_online': s.status in [LiveSource.Statuses.ONLINE, LiveSource.Statuses.RECORDING],
                    'is_recording': s.status == LiveSource.Statuses.RECORDING,
                    'building': s.building,
                    'room': s.room,
                    'floor': s.floor,
                    'source_type_label': source_type_label,
                    'stream_urls': s_urls,
                    'is_camera': False
                })
                
            if streams:
                region_streams[r] = streams

        context['region_streams'] = region_streams
        context['regions'] = regions_list
        context['search_query'] = search_query
        context['selected_region'] = region_id
        context['selected_building'] = building
        context['selected_status'] = status
        
        return context


class AdminDashboardView(SuperAdminRequiredMixin, TemplateView):
    """
    Super Admin Dashboard with global server statistics and charts.
    """
    template_name = 'dashboard/admin_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Basic stats
        total_regions = Region.objects.count()
        cameras = Camera.objects.all()
        total_cameras = cameras.count()
        online_cameras = cameras.filter(status=Camera.Statuses.ONLINE).count()
        offline_cameras = cameras.filter(status=Camera.Statuses.OFFLINE).count()
        
        # Current active streams count (StreamingLogs with no corresponding STOP, or estimated active paths)
        # We can calculate current streams from cameras with online status
        current_streams = online_cameras
        
        # Server health calculations
        total, used, free = shutil.disk_usage("c:/")  # Windows main drive
        disk_used_percent = (used / total) * 100
        
        cpu_percent = 12.5
        mem_percent = 40.0
        try:
            import psutil
            cpu_percent = psutil.cpu_percent(interval=None)
            mem_percent = psutil.virtual_memory().percent
        except ImportError:
            pass

        # Load from health checks cache
        from django.core.cache import cache
        health_metrics = cache.get("server_health_metrics")
        context['health_metrics'] = health_metrics
        if health_metrics:
            cpu_percent = health_metrics.get("cpu", cpu_percent)
            mem_percent = health_metrics.get("memory", mem_percent)
            disk_used_percent = health_metrics.get("disk", disk_used_percent)

        # Logs and activities
        recent_logs = ActivityLog.objects.select_related('user').order_by('-timestamp')[:5]
        
        # Build context stats
        context['stats'] = {
            'total_regions': total_regions,
            'total_cameras': total_cameras,
            'online_cameras': online_cameras,
            'offline_cameras': offline_cameras,
            'current_streams': current_streams,
            'bandwidth': round(current_streams * 2.5, 1), # mock bandwidth: 2.5 Mbps per active stream
            'disk_used': round(disk_used_percent, 1),
            'cpu_used': round(cpu_percent, 1),
            'mem_used': round(mem_percent, 1),
        }
        
        context['recent_logs'] = recent_logs
        
        # Data for charts (JSON serialize ready)
        context['chart_status_data'] = [online_cameras, offline_cameras, total_cameras - online_cameras - offline_cameras]
        
        region_stats = []
        region_labels = []
        for r in Region.objects.all():
            region_labels.append(r.name)
            region_stats.append(r.cameras.count())
        context['chart_regions'] = region_labels
        context['chart_region_cameras'] = region_stats
        
        return context


class RegionDashboardView(RegionAdminRequiredMixin, TemplateView):
    """
    Region Administrator Dashboard showing statistics for their own campus.
    """
    template_name = 'dashboard/region_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        region = self.request.user.region
        
        cameras = Camera.objects.filter(region=region)
        total_cameras = cameras.count()
        online_cameras = cameras.filter(status=Camera.Statuses.ONLINE).count()
        offline_cameras = cameras.filter(status=Camera.Statuses.OFFLINE).count()
        
        context['region'] = region
        context['stats'] = {
            'total_cameras': total_cameras,
            'online_cameras': online_cameras,
            'offline_cameras': offline_cameras,
            'current_streams': online_cameras,
        }
        
        # Inject stream URLs for viewing on the dashboard
        for c in cameras:
            c.stream_urls = MediaMTXService.get_stream_urls(c)
            
        context['cameras'] = cameras
        
        return context
