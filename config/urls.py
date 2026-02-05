from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse


def health_check(request):
    """
    Health check endpoint for Render and monitoring.
    Returns 200 OK if the service is running.
    """
    return JsonResponse({"status": "ok", "service": "clinicflow-backend"})


urlpatterns = [
    # Health check (no auth required)
    path("health/", health_check, name="health_check"),
    path("api/health/", health_check, name="api_health_check"),

    # Admin
    path("admin/", admin.site.urls),

    # API routes
    path("api/auth/", include("accounts.urls")),
    path("api/patients/", include("patients.urls")),
    path("api/visits/", include("visits.urls")),
    path("api/prescriptions/", include("prescriptions.urls")),
    path("api/appointments/", include("appointments.urls")),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
