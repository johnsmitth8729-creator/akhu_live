from django.urls import path, include
from rest_framework.routers import DefaultRouter
from core import api_views
from screens import api_views as screens_api
from sources import api_views as sources_api

app_name = 'api'

router = DefaultRouter()
router.register('regions', api_views.RegionViewSet, basename='regions')
router.register('cameras', api_views.CameraViewSet, basename='cameras')
router.register('streams', api_views.StreamingLogViewSet, basename='streams')
router.register('status', api_views.CameraStatusViewSet, basename='status')
router.register('logs', api_views.ActivityLogViewSet, basename='logs')
router.register('screens', screens_api.ComputerViewSet, basename='screens')
router.register('live-sources', sources_api.LiveSourceViewSet, basename='live-sources')
router.register('recordings', sources_api.RecordingViewSet, basename='recordings')

urlpatterns = [
    path('auth/', api_views.AuthAPIView.as_view(), name='auth'),
    path('screens/register/', screens_api.AgentRegisterAPIView.as_view(), name='screens_register'),
    path('screens/heartbeat/', screens_api.AgentHeartbeatAPIView.as_view(), name='screens_heartbeat'),
    path('screens/start/', screens_api.AgentStartStreamAPIView.as_view(), name='screens_start'),
    path('screens/stop/', screens_api.AgentStopStreamAPIView.as_view(), name='screens_stop'),
    path('screens/snapshot/', screens_api.ScreenSnapshotAPIView.as_view(), name='screens_snapshot'),
    
    path('start-stream/', sources_api.StartStreamAPIView.as_view(), name='start_stream'),
    path('stop-stream/', sources_api.StopStreamAPIView.as_view(), name='stop_stream'),
    path('start-record/', sources_api.StartRecordAPIView.as_view(), name='start_record'),
    path('stop-record/', sources_api.StopRecordAPIView.as_view(), name='stop_record'),
    path('', include(router.urls)),
]
