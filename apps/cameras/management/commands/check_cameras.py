from django.core.management.base import BaseCommand
from cameras.models import Camera
from cameras.services import update_camera_status

class Command(BaseCommand):
    help = 'Poll and update status of all configured IP cameras.'

    def handle(self, *args, **options):
        cameras = Camera.objects.all()
        self.stdout.write(f"Starting status check for {cameras.count()} cameras...")
        
        online_count = 0
        for camera in cameras:
            try:
                is_online = update_camera_status(camera)
                status_text = 'ONLINE' if is_online else 'OFFLINE'
                self.stdout.write(f"Camera: {camera.name} at {camera.ip_address} is {status_text}")
                if is_online:
                    online_count += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error checking camera {camera.name}: {e}"))
                
        self.stdout.write(self.style.SUCCESS(f"Finished check. {online_count} online, {cameras.count() - online_count} offline."))
