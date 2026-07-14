import requests
import logging
from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from sources.models import LiveSource, Recording
from sources.serializers import LiveSourceSerializer, RecordingSerializer
from logs.models import ActivityLog
from streaming.services import MediaMTXService

logger = logging.getLogger(__name__)

# Dynamic helper to register LiveSource RTSP paths on MediaMTX
def register_rtsp_source_path(source):
    stream_name = f"source_{source.id}"
    api_url = getattr(settings, 'MEDIAMTX_API_URL', 'http://127.0.0.1:9997')
    url = f"{api_url}/v3/config/paths/add/{stream_name}"
    
    rtsp_url = source.rtsp_url
    if source.rtsp_username and source.rtsp_password:
        if "@" not in rtsp_url:
            prefix = "rtsp://"
            if rtsp_url.startswith(prefix):
                creds = f"{source.rtsp_username}:{source.rtsp_password}@"
                rtsp_url = prefix + creds + rtsp_url[len(prefix):]
                
    payload = {
        "source": rtsp_url,
        "sourceOnDemand": True
    }
    timeout = 3
    try:
        logger.info(f"Sending MediaMTX API Request: POST {url} - Timeout: {timeout}s - Payload: {payload}")
        res = requests.post(url, json=payload, timeout=timeout)
        logger.info(f"MediaMTX API Response: POST {url} - Status Code: {res.status_code} - Body: {res.text}")
        if res.status_code in (200, 201):
            return True
        else:
            logger.error(f"MediaMTX API Error: POST {url} failed with status {res.status_code}. Response: {res.text}")
            return False
    except requests.exceptions.RequestException as e:
        logger.error(f"MediaMTX API Request Exception: POST {url} - Timeout: {timeout}s - Error: {e}")
        return False


def deregister_rtsp_source_path(source):
    stream_name = f"source_{source.id}"
    api_url = getattr(settings, 'MEDIAMTX_API_URL', 'http://127.0.0.1:9997')
    url = f"{api_url}/v3/config/paths/delete/{stream_name}"
    timeout = 3
    try:
        logger.info(f"Sending MediaMTX API Request: DELETE {url} - Timeout: {timeout}s")
        res = requests.delete(url, timeout=timeout)
        logger.info(f"MediaMTX API Response: DELETE {url} - Status Code: {res.status_code} - Body: {res.text}")
        if res.status_code in (200, 204):
            return True
        elif res.status_code == 404:
            logger.info(f"Stream {stream_name} did not exist on MediaMTX (404) during deregistration.")
            return True
        else:
            logger.error(f"MediaMTX API Error: DELETE {url} failed with status {res.status_code}. Response: {res.text}")
            return False
    except requests.exceptions.RequestException as e:
        logger.error(f"MediaMTX API Request Exception: DELETE {url} - Timeout: {timeout}s - Error: {e}")
        return False


class LiveSourceViewSet(viewsets.ModelViewSet):
    serializer_class = LiveSourceSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        # Allow read-only operations for anyone (public dashboard status checks)
        if self.action in ['list', 'retrieve']:
            return LiveSource.objects.all()
            
        # Restrict write operations to owners / super admins
        if user.is_authenticated:
            if user.is_super_admin():
                return LiveSource.objects.all()
            elif user.is_region_admin() and hasattr(user, 'region'):
                return LiveSource.objects.filter(region=user.region)
        return LiveSource.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        if user.is_region_admin():
            source = serializer.save(region=user.region)
        else:
            source = serializer.save()
            
        ActivityLog.objects.create(
            user=user,
            action='source_created',
            description=f"Live stream source '{source.name}' ({source.get_source_type_display()}) was created.",
            ip_address=self.request.META.get('REMOTE_ADDR')
        )

    def perform_destroy(self, instance):
        user = self.request.user
        # Cleanup from MediaMTX if RTSP
        if instance.source_type == LiveSource.SourceTypes.IP_CAMERA:
            deregister_rtsp_source_path(instance)
            
        ActivityLog.objects.create(
            user=user,
            action='source_deleted',
            description=f"Live stream source '{instance.name}' ({instance.get_source_type_display()}) was deleted.",
            ip_address=self.request.META.get('REMOTE_ADDR')
        )
        instance.delete()


class RecordingViewSet(viewsets.ModelViewSet):
    serializer_class = RecordingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_super_admin():
            return Recording.objects.all()
        elif user.is_region_admin() and hasattr(user, 'region'):
            return Recording.objects.filter(live_source__region=user.region)
        return Recording.objects.none()

    def perform_create(self, serializer):
        # Allow uploading recording files
        recording = serializer.save()
        ActivityLog.objects.create(
            user=self.request.user,
            action='recording_uploaded',
            description=f"Recording clip '{recording.filename}' ({recording.filesize} bytes) uploaded successfully.",
            ip_address=self.request.META.get('REMOTE_ADDR')
        )


class StartStreamAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        source_id = request.data.get('source_id')
        if not source_id:
            return Response({'detail': _('source_id is required.')}, status=status.HTTP_400_BAD_REQUEST)
            
        source = get_object_or_404(LiveSource, id=source_id)
        
        # Verify permissions
        if not request.user.is_super_admin() and source.region != request.user.region:
            return Response({'detail': _('Access denied.')}, status=status.HTTP_403_FORBIDDEN)
            
        # If IP Camera, dynamically register it in MediaMTX
        if source.source_type == LiveSource.SourceTypes.IP_CAMERA:
            register_rtsp_source_path(source)
            
        source.status = LiveSource.Statuses.ONLINE
        source.last_connected = timezone.now()
        source.save()
        
        ActivityLog.objects.create(
            user=request.user,
            action='source_stream_started',
            description=f"Stream session started on source '{source.name}' ({source.get_source_type_display()}).",
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        return Response({'status': 'ok', 'source_status': source.status})


class StopStreamAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        source_id = request.data.get('source_id')
        if not source_id:
            return Response({'detail': _('source_id is required.')}, status=status.HTTP_400_BAD_REQUEST)
            
        source = get_object_or_404(LiveSource, id=source_id)
        
        # Verify permissions
        if not request.user.is_super_admin() and source.region != request.user.region:
            return Response({'detail': _('Access denied.')}, status=status.HTTP_403_FORBIDDEN)
            
        # If IP Camera, deregister from MediaMTX
        if source.source_type == LiveSource.SourceTypes.IP_CAMERA:
            deregister_rtsp_source_path(source)
            
        source.status = LiveSource.Statuses.IDLE
        source.last_disconnected = timezone.now()
        source.save()
        
        ActivityLog.objects.create(
            user=request.user,
            action='source_stream_stopped',
            description=f"Stream session stopped on source '{source.name}' ({source.get_source_type_display()}).",
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        return Response({'status': 'ok', 'source_status': source.status})


class StartRecordAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        source_id = request.data.get('source_id')
        if not source_id:
            return Response({'detail': _('source_id is required.')}, status=status.HTTP_400_BAD_REQUEST)
            
        source = get_object_or_404(LiveSource, id=source_id)
        
        # Verify permissions
        if not request.user.is_super_admin() and source.region != request.user.region:
            return Response({'detail': _('Access denied.')}, status=status.HTTP_403_FORBIDDEN)
            
        source.status = LiveSource.Statuses.RECORDING
        source.recording_enabled = True
        source.save()
        
        ActivityLog.objects.create(
            user=request.user,
            action='source_recording_started',
            description=f"Active recording session started on stream source '{source.name}'.",
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        return Response({'status': 'ok', 'source_status': source.status})


class StopRecordAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        source_id = request.data.get('source_id')
        if not source_id:
            return Response({'detail': _('source_id is required.')}, status=status.HTTP_400_BAD_REQUEST)
            
        source = get_object_or_404(LiveSource, id=source_id)
        
        # Verify permissions
        if not request.user.is_super_admin() and source.region != request.user.region:
            return Response({'detail': _('Access denied.')}, status=status.HTTP_403_FORBIDDEN)
            
        source.status = LiveSource.Statuses.ONLINE
        source.save()
        
        ActivityLog.objects.create(
            user=request.user,
            action='source_recording_stopped',
            description=f"Active recording session stopped on stream source '{source.name}'.",
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        return Response({'status': 'ok', 'source_status': source.status})
