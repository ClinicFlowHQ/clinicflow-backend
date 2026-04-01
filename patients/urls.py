from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PatientListCreateView,
    PatientDetailView,
    archive_patient,
    restore_patient,
    latest_medical_history,
    PatientFileViewSet,
)

# Router for nested file resources
file_router = DefaultRouter()
file_router.register(r'files', PatientFileViewSet, basename='patient-files')

urlpatterns = [
    path("", PatientListCreateView.as_view(), name="patient_list_create"),
    path("<int:pk>/", PatientDetailView.as_view(), name="patient_detail"),
    path("<int:pk>/archive/", archive_patient, name="patient_archive"),
    path("<int:pk>/restore/", restore_patient, name="patient_restore"),
    path("<int:patient_id>/latest-medical-history/", latest_medical_history, name="patient_latest_medical_history"),
    # Nested file routes: /api/patients/<patient_id>/files/
    path("<int:patient_id>/", include(file_router.urls)),
]
