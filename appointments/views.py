from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Appointment
from .serializers import AppointmentSerializer, DoctorSerializer

User = get_user_model()


class DoctorListAPIView(APIView):
    """List users with doctor or nurse role for appointment assignment."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        # Get users who have a profile with role 'doctor' or 'nurse' (exclude admin)
        doctors = User.objects.filter(
            profile__role__in=['doctor', 'nurse']
        ).select_related('profile').order_by('first_name', 'last_name')
        serializer = DoctorSerializer(doctors, many=True)
        return Response(serializer.data)


class AppointmentListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = AppointmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = (
            Appointment.objects.select_related("patient", "visit", "doctor", "doctor__profile")
            .filter(patient__created_by=self.request.user)
            .order_by("-scheduled_at")
        )

        patient_id = self.request.query_params.get("patient")
        status_ = self.request.query_params.get("status")
        upcoming = self.request.query_params.get("upcoming")

        if patient_id:
            qs = qs.filter(patient_id=patient_id)

        if status_:
            qs = qs.filter(status=status_)

        if upcoming and upcoming.lower() == "true":
            qs = qs.filter(scheduled_at__gte=timezone.now()).exclude(
                status__in=["CANCELLED", "COMPLETED", "NO_SHOW"]
            )

        return qs

class AppointmentDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AppointmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Appointment.objects.select_related("patient", "visit", "doctor", "doctor__profile").filter(
            patient__created_by=self.request.user
        )
