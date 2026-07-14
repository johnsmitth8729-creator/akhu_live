from django.urls import path
from regions import views

app_name = 'regions'

urlpatterns = [
    path('', views.RegionListView.as_view(), name='list'),
    path('create/', views.RegionCreateView.as_view(), name='create'),
    path('<int:pk>/edit/', views.RegionUpdateView.as_view(), name='edit'),
    path('<int:pk>/delete/', views.RegionDeleteView.as_view(), name='delete'),
    path('<int:pk>/toggle/', views.RegionToggleStatusView.as_view(), name='toggle'),
    path('<int:pk>/reset-password/', views.RegionPasswordResetView.as_view(), name='reset_password'),
]
