from django.urls import path
from dashboard import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('admin-dashboard/', views.AdminDashboardView.as_view(), name='admin_dashboard'),
    path('region-dashboard/', views.RegionDashboardView.as_view(), name='region_dashboard'),
    path('api/dvr/<str:stream_id>/list/', views.DVRListView.as_view(), name='dvr_list'),
    path('api/dvr/<str:stream_id>/get/', views.DVRGetView.as_view(), name='dvr_get'),
]
