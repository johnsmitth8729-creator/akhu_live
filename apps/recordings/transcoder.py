import os
import shutil
import subprocess
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

class ABRTranscoderService:
    """
    Dedicated FFmpeg Transcoding Service for Adaptive Bitrate Streaming (ABR).
    Generates multi-rendition HLS playlists (1080p, 720p, 540p, 480p, 360p, 240p).
    If FFmpeg is unavailable, falls back gracefully to single-quality WHEP/HLS stream.
    """
    RENDITIONS = {
        '1080p': {'width': 1920, 'height': 1080, 'bitrate': '4500k', 'maxrate': '4800k', 'bufsize': '9000k'},
        '720p': {'width': 1280, 'height': 720, 'bitrate': '2500k', 'maxrate': '2700k', 'bufsize': '5000k'},
        '540p': {'width': 960, 'height': 540, 'bitrate': '1500k', 'maxrate': '1600k', 'bufsize': '3000k'},
        '480p': {'width': 854, 'height': 480, 'bitrate': '1200k', 'maxrate': '1300k', 'bufsize': '2400k'},
        '360p': {'width': 640, 'height': 360, 'bitrate': '800k', 'maxrate': '900k', 'bufsize': '1600k'},
        '240p': {'width': 426, 'height': 240, 'bitrate': '400k', 'maxrate': '450k', 'bufsize': '800k'},
    }

    @classmethod
    def is_ffmpeg_available(cls):
        """Checks if ffmpeg executable is present in PATH."""
        return shutil.which('ffmpeg') is not None

    @classmethod
    def generate_master_playlist_content(cls, stream_id, available_renditions=None):
        """
        Generates HLS Master Playlist (m3u8) string containing variant streams.
        """
        if not available_renditions:
            available_renditions = ['1080p', '720p', '540p', '480p', '360p', '240p']

        lines = ["#EXTM3U", "#EXT-X-VERSION:3"]

        bandwidth_map = {
            '1080p': (5000000, "1920x1080"),
            '720p': (2800000, "1280x720"),
            '540p': (1700000, "960x540"),
            '480p': (1400000, "854x480"),
            '360p': (900000, "640x360"),
            '240p': (450000, "426x240"),
        }

        for rend in available_renditions:
            if rend in bandwidth_map:
                bw, res = bandwidth_map[rend]
                lines.append(f'#EXT-X-STREAM-INF:BANDWIDTH={bw},RESOLUTION={res},NAME="{rend}"')
                lines.append(f'/api/dvr/{stream_id}/playlist_{rend}.m3u8')

        return "\n".join(lines)
