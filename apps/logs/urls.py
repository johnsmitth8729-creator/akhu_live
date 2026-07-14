from django.urls import path
from logs import views

app_name = 'logs'

urlpatterns = [
    path('', views.ActivityLogListView.as_view(), name='list'),
]
