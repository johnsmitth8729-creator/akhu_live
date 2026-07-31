from django.urls import path
from recordings import views, sse_views, api_views

app_name = 'recordings'

urlpatterns = [
    path('', views.RecordingListView.as_view(), name='list'),
    path('<uuid:pk>/', views.RecordingDetailView.as_view(), name='detail'),
    path('<uuid:pk>/edit/', views.RecordingUpdateView.as_view(), name='edit'),
    path('<uuid:pk>/delete/', views.RecordingDeleteView.as_view(), name='delete'),
    
    # SSE Stream & Viewer Status
    path('sse/<str:stream_id>/', sse_views.StreamSSEView.as_view(), name='sse_status'),
]
