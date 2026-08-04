from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)

class SettingsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'settings'

    def ready(self):
        import sys
        skip_commands = {'migrate', 'makemigrations', 'collectstatic', 'shell',
                         'createsuperuser', 'check', 'test', 'flush', 'dbshell'}
        if len(sys.argv) > 1 and sys.argv[1] in skip_commands:
            return
        try:
            from settings.models import SystemSetting
            from sources.models import StreamingSetting
            
            defaults = [
                ('system_name', 'AKHU Live Exam Monitor', 'Global system title displayed across header and pages.', 'string'),
                ('mediamtx_api_url', 'http://127.0.0.1:9997', 'Internal REST API URL for MediaMTX control service.', 'string'),
                ('mediamtx_hls_url', 'https://live.akhu.uz', 'Public HLS streaming gateway endpoint.', 'string'),
                ('mediamtx_webrtc_url', 'https://live.akhu.uz', 'Public WebRTC / WHEP low-latency stream endpoint.', 'string'),
                ('stun_server', 'stun:stun.l.google.com:19302', 'STUN server for ICE candidate NAT traversal.', 'string'),
                ('auto_reconnect_enabled', 'true', 'Enable WebRTC client automatic reconnection on network drops.', 'boolean'),
                ('health_check_interval', '30', 'System health check polling interval (seconds).', 'integer'),
            ]
            for key, val, desc, vtype in defaults:
                SystemSetting.objects.get_or_create(
                    key=key,
                    defaults={'value': val, 'description': desc, 'value_type': vtype}
                )
            StreamingSetting.objects.get_or_create(
                id=1,
                defaults={
                    'mediamtx_url': 'http://127.0.0.1:9997',
                    'mediamtx_webrtc_url': 'https://live.akhu.uz',
                    'mediamtx_hls_url': 'https://live.akhu.uz',
                    'stun_url': 'stun:stun.l.google.com:19302',
                    'domain': 'live.akhu.uz',
                    'https_enabled': True
                }
            )
        except Exception as e:
            logger.warning(f"Default SystemSettings auto-seed skipped: {e}")

