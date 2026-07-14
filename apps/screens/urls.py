from django.urls import path
from screens import views

app_name = 'screens'

urlpatterns = [
    path('<int:pk>/diagnostics/api/', views.ComputerDiagnosticsAPIView.as_view(), name='diagnostics_api'),
]
