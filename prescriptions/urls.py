from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PrescriptionViewSet,
    PrescriptionTemplateViewSet,
    MedicationViewSet,
)

router = DefaultRouter()

# IMPORTANT: register specific prefixes FIRST
router.register(r"templates", PrescriptionTemplateViewSet, basename="prescription-template")
router.register(r"medications", MedicationViewSet, basename="medication")

# Register "" LAST so it doesn't swallow "templates" as a pk
router.register(r"", PrescriptionViewSet, basename="prescription")

urlpatterns = [
    path("", include(router.urls)),
]
