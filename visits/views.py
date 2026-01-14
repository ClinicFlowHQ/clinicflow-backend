# visits/views.py
from rest_framework import generics, permissions
from rest_framework.exceptions import PermissionDenied

from .models import Visit, VitalSign
from .serializers import VisitSerializer, VitalSignSerializer


class VisitListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = VisitSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Only visits for patients owned by the logged-in doctor.
        Optional filter: ?patient=<patient_id>
        """
        qs = (
            Visit.objects.select_related("patient", "patient__created_by")
            .filter(patient__created_by=self.request.user)
            .order_by("-visit_date")
        )

        patient_id = self.request.query_params.get("patient")
        if patient_id:
            qs = qs.filter(patient_id=patient_id)

        return qs

    def perform_create(self, serializer):
        """
        Prevent creating a visit for someone else's patient.
        """
        patient = serializer.validated_data.get("patient")
        if not patient:
            raise PermissionDenied("Patient is required.")
        if patient.created_by_id != self.request.user.id:
            raise PermissionDenied("You cannot create a visit for this patient.")

        serializer.save()


class VisitDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = VisitSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            Visit.objects.select_related("patient", "patient__created_by")
            .filter(patient__created_by=self.request.user)
        )


class VitalSignListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = VitalSignSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Only vitals for visits that belong to my patients.
        Optional filter: ?visit=<visit_id>
        """
        qs = (
            VitalSign.objects.select_related(
                "visit",
                "visit__patient",
                "visit__patient__created_by",
            )
            .filter(visit__patient__created_by=self.request.user)
            .order_by("-measured_at")
        )

        visit_id = self.request.query_params.get("visit")
        if visit_id:
            qs = qs.filter(visit_id=visit_id)

        return qs

    def perform_create(self, serializer):
        """
        Prevent creating vitals for a visit that doesn't belong to my patients.
        """
        visit = serializer.validated_data.get("visit")
        if not visit:
            raise PermissionDenied("Visit is required.")

        if visit.patient.created_by_id != self.request.user.id:
            raise PermissionDenied("You cannot add vitals to this visit.")

        serializer.save()


class VitalSignDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = VitalSignSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            VitalSign.objects.select_related(
                "visit",
                "visit__patient",
                "visit__patient__created_by",
            )
            .filter(visit__patient__created_by=self.request.user)
        )
