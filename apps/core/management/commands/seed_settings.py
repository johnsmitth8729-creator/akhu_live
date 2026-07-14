from django.core.management.base import BaseCommand
from settings.models import SystemSetting

class Command(BaseCommand):
    help = 'Seed default system settings into the database.'

    def handle(self, *args, **options):
        default_settings = [
            {
                'key': 'system_name',
                'value': 'AKHU Live Exam Monitor',
                'description': 'The portal title displayed in header and tabs.',
                'value_type': SystemSetting.ValueTypes.STRING
            },
            {
                'key': 'mediamtx_api_url',
                'value': 'http://127.0.0.1:9997',
                'description': 'The REST API endpoint for MediaMTX.',
                'value_type': SystemSetting.ValueTypes.STRING
            },
            {
                'key': 'mediamtx_webrtc_url',
                'value': 'http://127.0.0.1:8889',
                'description': 'WebRTC connection base URL.',
                'value_type': SystemSetting.ValueTypes.STRING
            },
            {
                'key': 'mediamtx_hls_url',
                'value': 'http://127.0.0.1:8888',
                'description': 'HLS connection base URL.',
                'value_type': SystemSetting.ValueTypes.STRING
            },
            {
                'key': 'auto_status_check_enabled',
                'value': 'true',
                'description': 'Enable background TCP polling checks.',
                'value_type': SystemSetting.ValueTypes.BOOLEAN
            },
            {
                'key': 'screen_streaming_quality',
                'value': 'high',
                'description': 'Screen sharing video quality (low, medium, high).',
                'value_type': SystemSetting.ValueTypes.STRING
            },
            {
                'key': 'screen_fps',
                'value': '15',
                'description': 'Target framerate (FPS) for screen capture agent.',
                'value_type': SystemSetting.ValueTypes.INTEGER
            },
            {
                'key': 'screen_bitrate',
                'value': '1500',
                'description': 'Maximum video encoding bitrate (Kbps) for agent stream.',
                'value_type': SystemSetting.ValueTypes.INTEGER
            },
            {
                'key': 'screen_heartbeat_interval',
                'value': '10',
                'description': 'Heartbeat reporting interval (seconds) for agents.',
                'value_type': SystemSetting.ValueTypes.INTEGER
            },
            {
                'key': 'screen_snapshot_quality',
                'value': '85',
                'description': 'JPEG/PNG compression factor for admin screen snapshots.',
                'value_type': SystemSetting.ValueTypes.INTEGER
            },
            {
                'key': 'screen_reconnect_timeout',
                'value': '5',
                'description': 'Wait duration (seconds) before agent attempts streaming reconnection.',
                'value_type': SystemSetting.ValueTypes.INTEGER
            }
        ]

        created_count = 0
        for s in default_settings:
            setting, created = SystemSetting.objects.get_or_create(
                key=s['key'],
                defaults={
                    'value': s['value'],
                    'description': s['description'],
                    'value_type': s['value_type']
                }
            )
            if created:
                created_count += 1

        self.stdout.write(self.style.SUCCESS(f"Successfully seeded {created_count} default system settings."))
