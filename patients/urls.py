from django.urls import path
from .views import PatientListCreateView, PatientDetailView, archive_patient, restore_patient

urlpatterns = [
    path("", PatientListCreateView.as_view(), name="patient_list_create"),
    path("<int:pk>/", PatientDetailView.as_view(), name="patient_detail"),
    path("<int:pk>/archive/", archive_patient, name="patient_archive"),
    path("<int:pk>/restore/", restore_patient, name="patient_restore"),
]