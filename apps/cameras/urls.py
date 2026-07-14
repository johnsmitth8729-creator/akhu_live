from django.urls import path
from cameras import views

app_name = 'cameras'

urlpatterns = [
    path('', views.CameraListView.as_view(), name='list'),
    path('create/', views.CameraCreateView.as_view(), name='create'),
    path('<int:pk>/edit/', views.CameraUpdateView.as_view(), name='edit'),
    path('<int:pk>/delete/', views.CameraDeleteView.as_view(), name='delete'),
    path('<int:pk>/start-stream/', views.CameraStartStreamView.as_view(), name='start_stream'),
    path('<int:pk>/stop-stream/', views.CameraStopStreamView.as_view(), name='stop_stream'),
    path('<int:pk>/check-status/', views.CameraCheckStatusView.as_view(), name='check_status'),
]
