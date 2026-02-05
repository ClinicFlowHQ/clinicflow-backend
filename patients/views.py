# patients/views.py
from django.db.models import Max, Min, Q
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import generics, status, viewsets
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import Patient, PatientFile
from .serializers import PatientSerializer, PatientFileSerializer
from .pagination import PatientPagination
from .permissions import IsPatientOwnerOrAdmin, IsPatientFileOwnerOrAdmin

from visits.models import Visit


class PatientListCreateView(generics.ListCreateAPIView):
    serializer_class = PatientSerializer
    permission_classes = [IsAuthenticated]

    pagination_class = PatientPagination
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = [
        "patient_code",
        "first_name",
        "last_name",
        "phone",
        "address",
    ]

    ordering_fields = [
        "last_name",
        "first_name",
        "created_at",
        "patient_code",
        "last_visit_date",
        "next_visit_date",
    ]
    ordering = ["last_name", "first_name"]

    def get_queryset(self):
        now = timezone.now()
        user = self.request.user
        is_admin = hasattr(user, 'profile') and user.profile.role == 'admin'

        # All authenticated staff can see all patients
        qs = Patient.objects.all()

        # Filter by is_active status (default: show only active)
        # Only admins can view archived patients
        show_archived = self.request.query_params.get('archived', 'false').lower() == 'true'
        if show_archived and is_admin:
            qs = qs.filter(is_active=False)  # ONLY archived
        else:
            qs = qs.filter(is_active=True)   # default: active only

        return (
            qs.annotate(
                # Latest visit that already happened (<= now)
                last_visit_date=Max(
                    "visits__visit_date",
                    filter=Q(visits__visit_date__lte=now),
                ),
                # Next upcoming visit (> now)
                next_visit_date=Min(
                    "visits__visit_date",
                    filter=Q(visits__visit_date__gt=now),
                ),
            )
            .order_by("last_name", "first_name")
        )

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class PatientDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = PatientSerializer
    permission_classes = [IsAuthenticated, IsPatientOwnerOrAdmin]

    def get_queryset(self):
        now = timezone.now()

        # All authenticated staff can access any patient
        qs = Patient.objects.all()

        return (
            qs.annotate(
                last_visit_date=Max(
                    "visits__visit_date",
                    filter=Q(visits__visit_date__lte=now),
                ),
                next_visit_date=Min(
                    "visits__visit_date",
                    filter=Q(visits__visit_date__gt=now),
                ),
            )
        )

    def perform_destroy(self, instance):
        # Soft delete: set is_active to False instead of deleting
        instance.is_active = False
        instance.save()


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def archive_patient(request, pk):
    """Archive a patient (soft delete). Admin can archive any, others only their own."""
    user = request.user
    is_admin = hasattr(user, 'profile') and user.profile.role == 'admin'

    patient = get_object_or_404(Patient, pk=pk)

    if not is_admin and patient.created_by != user:
        return Response(
            {"detail": "You do not have permission to archive this patient."},
            status=status.HTTP_403_FORBIDDEN
        )

    if not patient.is_active:
        return Response(
            {"detail": "Patient is already archived."},
            status=status.HTTP_400_BAD_REQUEST
        )

    patient.is_active = False
    patient.save()
    return Response({"detail": "Patient archived successfully."})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def restore_patient(request, pk):
    """Restore an archived patient. Admin only."""
    user = request.user
    is_admin = hasattr(user, 'profile') and user.profile.role == 'admin'

    if not is_admin:
        return Response(
            {"detail": "Only administrators can restore patients."},
            status=status.HTTP_403_FORBIDDEN
        )

    try:
        patient = Patient.objects.get(pk=pk)
    except Patient.DoesNotExist:
        return Response(
            {"detail": "Patient not found."},
            status=status.HTTP_404_NOT_FOUND
        )

    if patient.is_active:
        return Response(
            {"detail": "Patient is not archived."},
            status=status.HTTP_400_BAD_REQUEST
        )

    patient.is_active = True
    patient.save()
    return Response({"detail": "Patient restored successfully."})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def latest_medical_history(request, patient_id):
    """
    GET /api/patients/<patient_id>/latest-medical-history/
    Returns the most recent non-empty medical_history from the patient's visits.
    """
    get_object_or_404(Patient, pk=patient_id)

    medical_history = (
        Visit.objects
        .filter(patient_id=patient_id)
        .exclude(medical_history="")
        .order_by("-visit_date", "-created_at")
        .values_list("medical_history", flat=True)
        .first()
    ) or ""

    return Response({"medical_history": medical_history})


class PatientFileViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing patient files.

    Endpoints:
    - GET    /api/patients/{patient_id}/files/          - List files
    - POST   /api/patients/{patient_id}/files/          - Upload file
    - GET    /api/patients/{patient_id}/files/{id}/     - Get file details
    - DELETE /api/patients/{patient_id}/files/{id}/     - Delete file
    - GET    /api/patients/{patient_id}/files/{id}/download/ - Download file
    """
    serializer_class = PatientFileSerializer
    permission_classes = [IsAuthenticated, IsPatientFileOwnerOrAdmin]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        patient_id = self.kwargs.get('patient_id')
        return PatientFile.objects.filter(patient_id=patient_id)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def perform_create(self, serializer):
        patient_id = self.kwargs.get('patient_id')
        patient = get_object_or_404(Patient, pk=patient_id)

        # Check ownership for create (object-level permission won't fire on create)
        user = self.request.user
        is_admin = hasattr(user, 'profile') and user.profile.role == 'admin'
        if not is_admin and patient.created_by != user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You do not have permission to upload files for this patient.")

        serializer.save(patient=patient)

    @action(detail=True, methods=['get'])
    def download(self, request, patient_id=None, pk=None):
        """Download the file."""
        file_obj = self.get_object()
        response = FileResponse(
            file_obj.file.open('rb'),
            content_type=file_obj.file_type
        )
        response['Content-Disposition'] = f'attachment; filename="{file_obj.original_filename}"'
        return response
