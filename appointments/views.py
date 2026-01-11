from rest_framework import generics, permissions
from .models import Appointment
from .serializers import AppointmentSerializer


class AppointmentListCreateAPIView(generics.ListCreateAPIView):
    queryset = Appointment.objects.select_related("patient", "visit").all()
    serializer_class = AppointmentSerializer
    permission_classes = [permissions.IsAuthenticated]


class AppointmentDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Appointment.objects.select_related("patient", "visit").all()
    serializer_class = AppointmentSerializer
    permission_classes = [permissions.IsAuthenticated]