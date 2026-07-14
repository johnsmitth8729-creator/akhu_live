import requests
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class MediaMTXService:
    @staticmethod
    def get_api_url():
        try:
            from sources.models import StreamingSetting
            db_settings = StreamingSetting.objects.first()
            if db_settings:
                return db_settings.mediamtx_url
        except Exception as e:
            logger.warning(f"Failed to fetch MediaMTX API URL from database StreamingSetting: {e}")
        return getattr(settings, 'MEDIAMTX_API_URL', 'http://127.0.0.1:9997')

    @classmethod
    def add_camera_path(cls, camera):
        """
        Register a camera's RTSP URL dynamically in MediaMTX.
        """
        stream_name = f"camera_{camera.id}"
        url = f"{cls.get_api_url()}/v3/config/paths/add/{stream_name}"
        
        # Format credentials in the RTSP URL if provided
        rtsp_url = camera.rtsp_url
        if camera.username and camera.password:
            # Check if credentials are already in rtsp://
            if "@" not in rtsp_url:
                prefix = "rtsp://"
                if rtsp_url.startswith(prefix):
                    creds = f"{camera.username}:{camera.password}@"
                    rtsp_url = prefix + creds + rtsp_url[len(prefix):]
                    
        payload = {
            "source": rtsp_url,
            "sourceOnDemand": True
        }
        
        timeout = 3
        try:
            logger.info(f"Sending MediaMTX API Request: POST {url} - Timeout: {timeout}s - Payload: {payload}")
            response = requests.post(url, json=payload, timeout=timeout)
            logger.info(f"MediaMTX API Response: POST {url} - Status Code: {response.status_code} - Body: {response.text}")
            if response.status_code in (200, 201):
                logger.info(f"Successfully registered stream {stream_name} on MediaMTX.")
                return True
            else:
                logger.error(f"MediaMTX API Error: POST {url} failed with status {response.status_code}. Response: {response.text}")
                return False
        except requests.exceptions.RequestException as e:
            logger.error(f"MediaMTX API Request Exception: POST {url} - Timeout: {timeout}s - Error: {e}")
            return False

    @classmethod
    def remove_camera_path(cls, camera):
        """
        Remove a camera's path from MediaMTX.
        """
        stream_name = f"camera_{camera.id}"
        url = f"{cls.get_api_url()}/v3/config/paths/delete/{stream_name}"
        
        timeout = 3
        try:
            logger.info(f"Sending MediaMTX API Request: DELETE {url} - Timeout: {timeout}s")
            response = requests.delete(url, timeout=timeout)
            logger.info(f"MediaMTX API Response: DELETE {url} - Status Code: {response.status_code} - Body: {response.text}")
            if response.status_code in (200, 204):
                logger.info(f"Successfully removed stream {stream_name} from MediaMTX.")
                return True
            elif response.status_code == 404:
                logger.info(f"Stream {stream_name} did not exist on MediaMTX (404) during deregistration.")
                return True
            else:
                logger.error(f"MediaMTX API Error: DELETE {url} failed with status {response.status_code}. Response: {response.text}")
                return False
        except requests.exceptions.RequestException as e:
            logger.error(f"MediaMTX API Request Exception: DELETE {url} - Timeout: {timeout}s - Error: {e}")
            return False

    @classmethod
    def get_stream_urls(cls, camera):
        """
        Get the HLS and WebRTC URLs for a camera.
        """
        stream_name = f"camera_{camera.id}"
        
        try:
            from sources.models import StreamingSetting
            db_settings = StreamingSetting.objects.first()
        except Exception:
            db_settings = None

        if db_settings:
            hls_base = db_settings.mediamtx_hls_url
            webrtc_base = db_settings.mediamtx_webrtc_url
        else:
            hls_base = getattr(settings, 'MEDIAMTX_HLS_URL', 'http://127.0.0.1:8888')
            webrtc_base = getattr(settings, 'MEDIAMTX_WEBRTC_URL', 'http://127.0.0.1:8889')
        
        return {
            "hls": f"{hls_base}/{stream_name}/index.m3u8",
            "webrtc": f"{webrtc_base}/{stream_name}/",
            "whep": f"{webrtc_base}/{stream_name}/whep",
        }
