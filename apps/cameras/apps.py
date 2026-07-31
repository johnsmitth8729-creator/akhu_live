from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class CamerasConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'cameras'

    def ready(self):
        """Auto-register all active cameras in MediaMTX when Django starts."""
        import os
        # Skip in management commands like migrate, collectstatic, shell etc.
        import sys
        skip_commands = {'migrate', 'makemigrations', 'collectstatic', 'shell',
                         'createsuperuser', 'check', 'test', 'flush', 'dbshell'}
        if len(sys.argv) > 1 and sys.argv[1] in skip_commands:
            return
        # Skip during migrations (RUN_MAIN is set by runserver auto-reloader)
        # In production (gunicorn), always run.
        try:
            from streaming.services import MediaMTXService
            from cameras.models import Camera
            cameras = Camera.objects.all()
            count = 0
            for camera in cameras:
                try:
                    ok = MediaMTXService.add_camera_path(camera)
                    if ok:
                        count += 1
                except Exception as e:
                    logger.warning(f"Could not register camera {camera.id} in MediaMTX: {e}")
            logger.info(f"[CamerasConfig.ready] Auto-registered {count}/{cameras.count()} cameras in MediaMTX.")
        except Exception as e:
            logger.warning(f"[CamerasConfig.ready] MediaMTX auto-registration skipped: {e}")
