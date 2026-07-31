import os
import requests
import logging
from django.utils import timezone
from django.conf import settings
from django.db import transaction
from sources.models import LiveSource, StreamingSetting
from cameras.models import Camera
from recordings.models import LiveSession, RecordingSession, StoragePolicy, QualityRendition

logger = logging.getLogger(__name__)

from django.db.models import Q

class RecordingService:
    @staticmethod
    def get_mediamtx_api_url():
        try:
            db_settings = StreamingSetting.objects.first()
            if db_settings:
                return db_settings.mediamtx_url
        except Exception:
            pass
        return getattr(settings, 'MEDIAMTX_API_URL', 'http://127.0.0.1:9997')

    @classmethod
    def start_live_session(cls, source=None, camera=None, title=None, user=None):
        """
        Atomically starts a LiveSession and RecordingSession when stream starts.
        Enforces one-click automatic live session & recording creation.
        """
        with transaction.atomic():
            stream_id = ""
            region = None
            session_title = title or "Live Broadcast"

            if source:
                stream_id = f"source_{source.id}"
                region = source.region
                session_title = title or f"{source.name} Live"
                # Update source status to RECORDING (auto-recording)
                source.status = LiveSource.Statuses.RECORDING
                source.recording_enabled = True
                source.last_connected = timezone.now()
                source.save(update_fields=['status', 'recording_enabled', 'last_connected'])

            elif camera:
                stream_id = f"camera_{camera.id}"
                region = camera.region
                session_title = title or f"{camera.name} Live"
                camera.status = Camera.Statuses.ONLINE
                camera.last_seen = timezone.now()
                camera.save(update_fields=['status', 'last_seen'])

            # Close any orphaned active sessions for this stream_id
            cls.end_live_session(stream_id=stream_id)

            now = timezone.now()
            live_session = LiveSession.objects.create(
                source=source,
                camera=camera,
                region=region,
                stream_id=stream_id,
                title=session_title,
                status=LiveSession.Statuses.LIVE,
                started_at=now
            )

            # Generate filename & file path according to standard hierarchy: Year/Month/Day/Region
            year = now.strftime('%Y')
            month = now.strftime('%m')
            day = now.strftime('%d')
            reg_slug = region.name.replace(' ', '_').replace('/', '_') if region else 'default'
            timestamp_str = now.strftime('%Y%m%d_%H%M%S')
            filename = f"{stream_id}_{timestamp_str}.mp4"
            file_path = os.path.join("recordings", year, month, day, reg_slug, filename)

            recording_session = RecordingSession.objects.create(
                live_session=live_session,
                source=source,
                camera=camera,
                region=region,
                title=f"Recording - {session_title}",
                filename=filename,
                file_path=file_path,
                file_url=f"/media/{file_path}",
                status=RecordingSession.Statuses.RECORDING,
                started_at=now
            )

            # Create default renditions metadata (Auto, 1080p, 720p, 480p, 360p)
            renditions_data = [
                ('1080p', 1080, 1920, 4500),
                ('720p', 720, 1280, 2500),
                ('480p', 480, 854, 1200),
                ('360p', 360, 640, 700),
            ]
            for label, h, w, b in renditions_data:
                QualityRendition.objects.create(
                    live_session=live_session,
                    recording_session=recording_session,
                    label=label,
                    height=h,
                    width=w,
                    bitrate_kbps=b,
                    playlist_url=f"/api/dvr/{stream_id}/playlist_{label}.m3u8",
                    is_available=True
                )

            logger.info(f"Started LiveSession {live_session.id} & RecordingSession {recording_session.id} for {stream_id}")
            return live_session, recording_session

    @classmethod
    def end_live_session(cls, stream_id=None, source=None, camera=None):
        """
        Atomically closes active LiveSession and RecordingSession for a stream.
        """
        query = Q(status=LiveSession.Statuses.LIVE)
        if stream_id:
            query &= Q(stream_id=stream_id)
        if source:
            query &= Q(source=source)
        if camera:
            query &= Q(camera=camera)

        active_sessions = LiveSession.objects.filter(query)
        now = timezone.now()

        for session in active_sessions:
            session.status = LiveSession.Statuses.ENDED
            session.ended_at = now
            session.save(update_fields=['status', 'ended_at'])

            if hasattr(session, 'recording_session') and session.recording_session:
                rec = session.recording_session
                rec.status = RecordingSession.Statuses.COMPLETED
                rec.ended_at = now
                rec.duration_seconds = int((now - rec.started_at).total_seconds())
                
                # Check file size on disk if available
                full_disk_path = os.path.join(settings.MEDIA_ROOT, rec.file_path)
                if os.path.exists(full_disk_path):
                    rec.filesize_bytes = os.path.getsize(full_disk_path)
                
                rec.save(update_fields=['status', 'ended_at', 'duration_seconds', 'filesize_bytes'])
                logger.info(f"Ended RecordingSession {rec.id} for stream {session.stream_id}, duration: {rec.duration_seconds}s")

        # Revert source status if needed
        if source and source.status == LiveSource.Statuses.RECORDING:
            source.status = LiveSource.Statuses.IDLE
            source.last_disconnected = now
            source.save(update_fields=['status', 'last_disconnected'])

    @staticmethod
    def get_or_create_storage_policy():
        policy = StoragePolicy.objects.first()
        if not policy:
            policy = StoragePolicy.objects.create(
                retention_days=30,
                auto_cleanup_enabled=True,
                max_storage_gb=500,
                max_duration_hours=24,
                auto_delete_policy='oldest_first'
            )
        return policy

    @classmethod
    def apply_storage_retention_policy(cls):
        """
        Scans recordings and deletes files exceeding retention policy.
        """
        policy = cls.get_or_create_storage_policy()
        if not policy.auto_cleanup_enabled:
            return 0

        deleted_count = 0
        cutoff_date = timezone.now() - timezone.timedelta(days=policy.retention_days)
        old_recordings = RecordingSession.objects.filter(
            started_at__lt=cutoff_date,
            retention_policy__in=[RecordingSession.RetentionPolicies.DAYS_7, RecordingSession.RetentionPolicies.DAYS_14, RecordingSession.RetentionPolicies.DAYS_30]
        ).exclude(retention_policy=RecordingSession.RetentionPolicies.NEVER)

        for rec in old_recordings:
            full_path = os.path.join(settings.MEDIA_ROOT, rec.file_path)
            if os.path.exists(full_path):
                try:
                    os.remove(full_path)
                except Exception as e:
                    logger.error(f"Failed to delete old recording file {full_path}: {e}")
            rec.delete()
            deleted_count += 1

        logger.info(f"Storage retention cleanup deleted {deleted_count} expired recordings.")
        return deleted_count
