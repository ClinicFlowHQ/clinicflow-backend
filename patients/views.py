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
            pass  # Show all including archived
        else:
            qs = qs.filter(is_active=True)

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
    permission_classes = [IsAuthenticated]

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

    try:
        if is_admin:
            patient = Patient.objects.get(pk=pk)
        else:
            patient = Patient.objects.get(pk=pk, created_by=user)
    except Patient.DoesNotExist:
        return Response(
            {"detail": "Patient not found or you don't have permission."},
            status=status.HTTP_404_NOT_FOUND
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
    permission_classes = [IsAuthenticated]
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
