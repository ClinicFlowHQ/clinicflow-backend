from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("accounts.urls")),
    path("api/patients/", include("patients.urls")),
    path("api/visits/", include("visits.urls")),
    path("api/prescriptions/", include("prescriptions.urls")),
    path("api/appointments/", include("appointments.urls")),
]