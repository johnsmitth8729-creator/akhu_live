from django.urls import path
from sources import views

app_name = 'sources'

urlpatterns = [
    path('', views.LiveSourceListView.as_view(), name='list'),
    path('wizard/', views.LiveSourceCreateWizardView.as_view(), name='wizard'),
    path('<uuid:pk>/edit/', views.LiveSourceUpdateView.as_view(), name='edit'),
    path('<uuid:pk>/delete/', views.LiveSourceDeleteView.as_view(), name='delete'),
]
