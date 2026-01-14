# patients/views.py
from django.db.models import Max, Min, Q
from django.utils import timezone

from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
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

        return (
            Patient.objects.filter(created_by=self.request.user)
            .annotate(
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

        return (
            Patient.objects.filter(created_by=self.request.user)
            .annotate(
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
