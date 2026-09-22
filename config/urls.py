from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse, Http404
from django.db import connection
from django.views.generic import RedirectView
from accounts.views import manage_connections

def health_check(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
    except Exception:
        return HttpResponse('Database unavailable', status=503)
    return HttpResponse('OK', status=200)

def private_media(request, path):
    raise Http404

urlpatterns = [
    path('admin/', RedirectView.as_view(pattern_name='backoffice:dashboard', permanent=False)),
    path('manage/', include('backoffice.urls')),
    path('healthz', health_check, name='health_check'),
    path('accounts/3rdparty/', manage_connections, name='socialaccount_connections'),
    path('accounts/', include('allauth.urls')),
    path('accounts/', include('accounts.urls')),
    path('products/', include('products.urls')),
    path('orders/', include('orders.urls')),
    path('', include('core.urls')),
]

if settings.DEBUG:
    urlpatterns += [re_path(r'^media/wishes/(?P<path>.*)$', private_media)]
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
