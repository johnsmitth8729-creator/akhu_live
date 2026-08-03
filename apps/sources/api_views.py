import requests
import logging
from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from sources.models import LiveSource
from sources.serializers import LiveSourceSerializer
from logs.models import ActivityLog
from streaming.services import MediaMTXService

logger = logging.getLogger(__name__)


def register_rtsp_source_path(source):
    """Dynamically register an IP Camera RTSP path on MediaMTX."""
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

    payload = {"source": rtsp_url, "sourceOnDemand": True}
    try:
        res = requests.post(url, json=payload, timeout=3)
        if res.status_code in (200, 201):
            return True
        logger.error(f"MediaMTX register failed: {res.status_code} {res.text}")
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"MediaMTX register error: {e}")
        return False


def deregister_rtsp_source_path(source):
    """Remove an IP Camera RTSP path from MediaMTX."""
    stream_name = f"source_{source.id}"
    api_url = getattr(settings, 'MEDIAMTX_API_URL', 'http://127.0.0.1:9997')
    url = f"{api_url}/v3/config/paths/delete/{stream_name}"
    try:
        res = requests.delete(url, timeout=3)
        if res.status_code in (200, 204, 404):
            return True
        logger.error(f"MediaMTX deregister failed: {res.status_code} {res.text}")
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"MediaMTX deregister error: {e}")
        return False


class LiveSourceViewSet(viewsets.ModelViewSet):
    serializer_class = LiveSourceSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        if self.action in ['list', 'retrieve']:
            return LiveSource.objects.all()
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
        if instance.source_type == LiveSource.SourceTypes.IP_CAMERA:
            deregister_rtsp_source_path(instance)

        ActivityLog.objects.create(
            user=user,
            action='source_deleted',
            description=f"Live stream source '{instance.name}' ({instance.get_source_type_display()}) was deleted.",
            ip_address=self.request.META.get('REMOTE_ADDR')
        )
        instance.delete()


class StartStreamAPIView(APIView):
    """Start a live stream session (no recording)."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        source_id = request.data.get('source_id')
        if not source_id:
            return Response({'detail': _('source_id is required.')}, status=status.HTTP_400_BAD_REQUEST)

        source = get_object_or_404(LiveSource, id=source_id)

        if not request.user.is_super_admin() and source.region != request.user.region:
            return Response({'detail': _('Access denied.')}, status=status.HTTP_403_FORBIDDEN)

        # Register RTSP path in MediaMTX for IP cameras
        if source.source_type == LiveSource.SourceTypes.IP_CAMERA:
            register_rtsp_source_path(source)

        source.status = LiveSource.Statuses.ONLINE
        source.last_connected = timezone.now()
        source.save(update_fields=['status', 'last_connected'])

        ActivityLog.objects.create(
            user=request.user,
            action='source_stream_started',
            description=f"Stream started on source '{source.name}' ({source.get_source_type_display()}).",
            ip_address=request.META.get('REMOTE_ADDR')
        )

        return Response({
            'status': 'ok',
            'source_status': source.status,
            'stream_id': f"source_{source.id}",
        })


class StopStreamAPIView(APIView):
    """Stop a live stream session."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        source_id = request.data.get('source_id')
        if not source_id:
            return Response({'detail': _('source_id is required.')}, status=status.HTTP_400_BAD_REQUEST)

        source = get_object_or_404(LiveSource, id=source_id)

        if not request.user.is_super_admin() and source.region != request.user.region:
            return Response({'detail': _('Access denied.')}, status=status.HTTP_403_FORBIDDEN)

        if source.source_type == LiveSource.SourceTypes.IP_CAMERA:
            deregister_rtsp_source_path(source)

        source.status = LiveSource.Statuses.IDLE
        source.last_disconnected = timezone.now()
        source.save(update_fields=['status', 'last_disconnected'])

        ActivityLog.objects.create(
            user=request.user,
            action='source_stream_stopped',
            description=f"Stream stopped on source '{source.name}' ({source.get_source_type_display()}).",
            ip_address=request.META.get('REMOTE_ADDR')
        )

        return Response({'status': 'ok', 'source_status': source.status})
