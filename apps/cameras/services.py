import socket
import time
from django.utils import timezone
from cameras.models import Camera, CameraStatus

def check_camera_connectivity(camera, timeout=2.0):
    """
    Test connectivity to a camera's IP and port using a TCP socket connection.
    Returns:
        (is_online, response_time_ms, error_message)
    """
    start_time = time.time()
    try:
        # Create a socket object
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        # Attempt to connect to the camera's IP and port (usually RTSP default 554)
        sock.connect((camera.ip_address, camera.port))
        sock.close()
        response_time = (time.time() - start_time) * 1000.0  # in ms
        return True, response_time, None
    except socket.timeout:
        return False, None, "Connection timed out"
    except socket.error as e:
        return False, None, f"Socket connection failed: {str(e)}"
    except Exception as e:
        return False, None, f"Unknown error: {str(e)}"

def update_camera_status(camera):
    """
    Check the camera's connectivity, log the status in CameraStatus history,
    and update the main Camera model status.
    """
    is_online, response_time, error_message = check_camera_connectivity(camera)
    status_str = Camera.Statuses.ONLINE if is_online else Camera.Statuses.OFFLINE
    
    # Update camera model status and last_seen
    camera.status = status_str
    if is_online:
        camera.last_seen = timezone.now()
    camera.save(update_fields=['status', 'last_seen'])
    
    # Log in CameraStatus database history
    CameraStatus.objects.create(
        camera=camera,
        status=status_str,
        response_time=response_time,
        error_message=error_message
    )
    
    return is_online
