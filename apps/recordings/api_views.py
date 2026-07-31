import os
import csv
import logging
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.conf import settings
from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from recordings.models import RecordingSession, LiveSession, StoragePolicy, QualityRendition
from recordings.serializers import RecordingSessionSerializer, LiveSessionSerializer, StoragePolicySerializer
from recordings.transcoder import ABRTranscoderService
from logs.models import ActivityLog

logger = logging.getLogger(__name__)

class RecordingSessionViewSet(viewsets.ModelViewSet):
    """
    REST API ViewSet for completed and active Recording Sessions.
    Provides search, filtering, pagination, rename, edit, download, bulk delete, export.
    """
    serializer_class = RecordingSessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = RecordingSession.objects.all()

        if not user.is_super_admin():
            if user.is_region_admin() and hasattr(user, 'region'):
                queryset = queryset.filter(region=user.region)
            else:
                return RecordingSession.objects.none()

        # Search filter
        search = self.request.query_params.get('search', '')
        if search:
            queryset = queryset.filter(title__icontains=search) | queryset.filter(filename__icontains=search)

        # Region filter
        region_id = self.request.query_params.get('region', '')
        if region_id:
            queryset = queryset.filter(region_id=region_id)

        # Status filter
        rec_status = self.request.query_params.get('status', '')
        if rec_status:
            queryset = queryset.filter(status=rec_status)

        return queryset.order_by('-started_at')

    def perform_destroy(self, instance):
        # Delete file on disk
        full_path = os.path.join(settings.MEDIA_ROOT, instance.file_path)
        if os.path.exists(full_path):
            try:
                os.remove(full_path)
            except Exception as e:
                logger.error(f"Error removing file {full_path}: {e}")

        ActivityLog.objects.create(
            user=self.request.user,
            action='recording_deleted',
            description=f"Recording session '{instance.title}' ({instance.filename}) was deleted.",
            ip_address=self.request.META.get('REMOTE_ADDR')
        )
        instance.delete()

    @action(detail=False, methods=['post'], url_path='bulk-delete')
    def bulk_delete(self, request):
        ids = request.data.get('ids', [])
        if not ids:
            return Response({'detail': 'No recording IDs provided.'}, status=status.HTTP_400_BAD_REQUEST)

        recordings = self.get_queryset().filter(id__in=ids)
        count = 0
        for rec in recordings:
            full_path = os.path.join(settings.MEDIA_ROOT, rec.file_path)
            if os.path.exists(full_path):
                try:
                    os.remove(full_path)
                except Exception as e:
                    logger.error(f"Error deleting file {full_path}: {e}")
            rec.delete()
            count += 1

        ActivityLog.objects.create(
            user=request.user,
            action='recordings_bulk_deleted',
            description=f"Bulk deleted {count} recording sessions.",
            ip_address=request.META.get('REMOTE_ADDR')
        )
        return Response({'status': 'ok', 'deleted_count': count})

    @action(detail=False, methods=['get'], url_path='export-csv')
    def export_csv(self, request):
        recordings = self.get_queryset()
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="recordings_export.csv"'

        writer = csv.writer(response)
        writer.writerow(['ID', 'Title', 'Filename', 'Region', 'Source/Camera', 'Started At', 'Duration (s)', 'Filesize (MB)', 'Status'])

        for r in recordings:
            source_name = r.source.name if r.source else (r.camera.name if r.camera else 'N/A')
            reg_name = r.region.name if r.region else 'N/A'
            writer.writerow([str(r.id), r.title, r.filename, reg_name, source_name, r.started_at, r.duration_seconds, r.filesize_mb, r.status])

        return response


class DVRMasterPlaylistAPIView(APIView):
    """
    Returns HLS Master Playlist for Adaptive Bitrate (ABR) streaming.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, stream_id):
        content = ABRTranscoderService.generate_master_playlist_content(stream_id)
        return HttpResponse(content, content_type='application/vnd.apple.mpegurl')


class StoragePolicyAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from recordings.services import RecordingService
        policy = RecordingService.get_or_create_storage_policy()
        serializer = StoragePolicySerializer(policy)
        return Response(serializer.data)

    def post(self, request):
        from recordings.services import RecordingService
        policy = RecordingService.get_or_create_storage_policy()
        serializer = StoragePolicySerializer(policy, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
