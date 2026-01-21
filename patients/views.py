# patients/views.py
from django.db.models import Max, Min, Q
from django.utils import timezone

from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import Patient
from .serializers import PatientSerializer
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

        # Base queryset - admins see all patients, others see only their own
        if is_admin:
            qs = Patient.objects.all()
        else:
            qs = Patient.objects.filter(created_by=user)

        # Filter by is_active status (default: show only active)
        show_archived = self.request.query_params.get('archived', 'false').lower() == 'true'
        if not show_archived:
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
        user = self.request.user
        is_admin = hasattr(user, 'profile') and user.profile.role == 'admin'

        # Admins can access any patient, others only their own
        if is_admin:
            qs = Patient.objects.all()
        else:
            qs = Patient.objects.filter(created_by=user)

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
