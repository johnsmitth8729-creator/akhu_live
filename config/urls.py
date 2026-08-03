from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns

from accounts.views import CustomLoginView

urlpatterns = [
    # REST API endpoints (non-i18n prefix)
    path('api/', include('config.api_urls', namespace='api')),
    # i18n language switch endpoint (POST request handles locale selection)
    path('i18n/', include('django.conf.urls.i18n')),
    # Direct /login shortcut route
    path('login/', CustomLoginView.as_view(), name='login_shortcut'),
]

# Wrap admin pages and app interfaces inside i18n prefix URLs
urlpatterns += i18n_patterns(
    path('admin/', admin.site.urls),
    path('login/', CustomLoginView.as_view(), name='login_shortcut_i18n'),
    path('accounts/', include('accounts.urls', namespace='accounts')),
    path('regions/', include('regions.urls', namespace='regions')),
    path('cameras/', include('cameras.urls', namespace='cameras')),
    path('screens/', include('screens.urls', namespace='screens')),
    path('sources/', include('sources.urls', namespace='sources')),
    path('logs/', include('logs.urls', namespace='logs')),
    path('settings/', include('settings.urls', namespace='settings')),
    path('', include('dashboard.urls', namespace='dashboard')),
)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
