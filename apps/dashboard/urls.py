from django.urls import path
from dashboard import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('admin-dashboard/', views.AdminDashboardView.as_view(), name='admin_dashboard'),
    path('region-dashboard/', views.RegionDashboardView.as_view(), name='region_dashboard'),
]
