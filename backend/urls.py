from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path


def health_check(request):
    return HttpResponse("ok")


urlpatterns = [
    path("healthz/", health_check),
    path("admin/", admin.site.urls),
    path("", include("backend.wedding.urls")),
]

if settings.DEBUG and not settings.USE_GCS_MEDIA and not settings.USE_GOOGLE_DRIVE_MEDIA:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
