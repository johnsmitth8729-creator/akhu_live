import time
import json
import logging
from django.http import StreamingHttpResponse
from django.views import View
from django.utils import timezone
from recordings.models import LiveSession, ViewerEvent

logger = logging.getLogger(__name__)

class StreamSSEView(View):
    """
    Server-Sent Events (SSE) view providing real-time viewer count, peak viewers,
    live status, and streaming duration without WebSockets or Django Channels.
    """
    def get(self, request, stream_id):
        # Register viewer join event
        session = LiveSession.objects.filter(stream_id=stream_id, status=LiveSession.Statuses.LIVE).first()
        viewer_ip = request.META.get('REMOTE_ADDR')
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:255]

        if session:
            try:
                ViewerEvent.objects.create(
                    live_session=session,
                    event_type=ViewerEvent.EventTypes.JOIN,
                    viewer_ip=viewer_ip,
                    user_agent=user_agent
                )
                session.current_viewers += 1
                session.total_views += 1
                if session.current_viewers > session.peak_viewers:
                    session.peak_viewers = session.current_viewers
                session.save(update_fields=['current_viewers', 'total_views', 'peak_viewers'])
            except Exception as e:
                logger.warning(f"Error registering viewer join event: {e}")

        def event_stream():
            try:
                while True:
                    active_session = LiveSession.objects.filter(stream_id=stream_id, status=LiveSession.Statuses.LIVE).first()
                    if active_session:
                        data = {
                            "is_live": True,
                            "viewers": active_session.current_viewers,
                            "peak_viewers": active_session.peak_viewers,
                            "total_views": active_session.total_views,
                            "duration_seconds": active_session.duration_seconds,
                            "resolution": active_session.resolution,
                            "fps": active_session.fps,
                            "status": active_session.status
                        }
                    else:
                        data = {
                            "is_live": False,
                            "viewers": 0,
                            "peak_viewers": 0,
                            "total_views": 0,
                            "duration_seconds": 0,
                            "resolution": "1080p",
                            "fps": 30,
                            "status": "idle"
                        }
                    
                    yield f"event: message\ndata: {json.dumps(data)}\n\n"
                    time.sleep(3)
            finally:
                # Register viewer leave event on disconnect
                if session:
                    try:
                        s = LiveSession.objects.filter(id=session.id).first()
                        if s and s.current_viewers > 0:
                            s.current_viewers -= 1
                            s.save(update_fields=['current_viewers'])
                        ViewerEvent.objects.create(
                            live_session=session,
                            event_type=ViewerEvent.EventTypes.LEAVE,
                            viewer_ip=viewer_ip,
                            user_agent=user_agent
                        )
                    except Exception as e:
                        logger.warning(f"Error registering viewer leave event: {e}")

        response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'  # Disable Nginx buffering for SSE
        return response
