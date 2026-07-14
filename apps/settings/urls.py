from django.urls import path
from settings import views

app_name = 'settings'

urlpatterns = [
    path('', views.SystemSettingListView.as_view(), name='list'),
    path('update/', views.SystemSettingUpdateView.as_view(), name='update'),
]
