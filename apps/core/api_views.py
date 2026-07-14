from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.contrib.auth import authenticate, login, logout
from django.utils.translation import gettext_lazy as _
from regions.models import Region
from cameras.models import Camera, CameraStatus
from logs.models import ActivityLog
from streaming.models import StreamingLog
from core.serializers import (
    RegionSerializer, CameraSerializer, CameraStatusSerializer, 
    ActivityLogSerializer, StreamingLogSerializer
)

class AuthAPIView(APIView):
    """
    API for Session Authentication (Login/Logout checks).
    """
    permission_classes = [permissions.AllowAny]
    
    def get(self, request):
        if request.user.is_authenticated:
            return Response({
                'authenticated': True,
                'username': request.user.username,
                'role': request.user.role
            })
        return Response({'authenticated': False})
    
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return Response({
                'detail': _('Successfully logged in.'),
                'username': user.username,
                'role': user.role
            })
        return Response({'detail': _('Invalid credentials.')}, status=status.HTTP_400_BAD_REQUEST)
        
    def delete(self, request):
        logout(request)
        return Response({'detail': _('Successfully logged out.')})


class RegionViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows regions to be viewed or edited.
    """
    serializer_class = RegionSerializer
    
    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Region.objects.none()
        if user.is_super_admin():
            return Region.objects.all()
        # Region Admin can only see their own region configuration
        if hasattr(user, 'region'):
            return Region.objects.filter(id=user.region.id)
        return Region.objects.none()
        
    def get_permissions(self):
        # Only Super Admin can create or delete regions
        if self.action in ['create', 'destroy']:
            return [permissions.IsAuthenticated(), permissions.IsAdminUser()]
        return [permissions.IsAuthenticated()]


class CameraViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows cameras to be viewed or edited.
    """
    serializer_class = CameraSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.is_super_admin():
            return Camera.objects.all()
        elif user.is_region_admin() and hasattr(user, 'region'):
            return Camera.objects.filter(region=user.region)
        return Camera.objects.none()
        
    def perform_create(self, serializer):
        user = self.request.user
        if user.is_region_admin():
            serializer.save(region=user.region)
        else:
            serializer.save()


class StreamingLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing streaming logs.
    """
    serializer_class = StreamingLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.is_super_admin():
            return StreamingLog.objects.all()
        elif user.is_region_admin() and hasattr(user, 'region'):
            return StreamingLog.objects.filter(camera__region=user.region)
        return StreamingLog.objects.none()


class CameraStatusViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing camera connectivity logs.
    """
    serializer_class = CameraStatusSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.is_super_admin():
            return CameraStatus.objects.all()
        elif user.is_region_admin() and hasattr(user, 'region'):
            return CameraStatus.objects.filter(camera__region=user.region)
        return CameraStatus.objects.none()


class ActivityLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing system audit activities (Super Admin only).
    """
    serializer_class = ActivityLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.is_super_admin():
            return ActivityLog.objects.all()
        return ActivityLog.objects.none()


class HealthCheckAPIView(APIView):
    """
    Lightweight health check endpoint returning system status.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        from django.db import connection
        from django.core.cache import cache
        
        status_data = {
            "status": "healthy",
            "database": "online",
            "cache": "online"
        }
        
        # Check DB
        try:
            connection.ensure_connection()
        except Exception:
            status_data["database"] = "offline"
            status_data["status"] = "unhealthy"

        # Check Cache (Redis)
        try:
            cache.set("__health_check_ping__", "pong", timeout=5)
            if cache.get("__health_check_ping__") != "pong":
                status_data["cache"] = "offline"
                status_data["status"] = "unhealthy"
        except Exception:
            status_data["cache"] = "offline"
            status_data["status"] = "unhealthy"

        response_status = status.HTTP_200_OK if status_data["status"] == "healthy" else status.HTTP_503_SERVICE_UNAVAILABLE
        return Response(status_data, status=response_status)
