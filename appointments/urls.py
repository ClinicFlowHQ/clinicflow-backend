from django.urls import path
from .views import AppointmentListCreateAPIView, AppointmentDetailAPIView

urlpatterns = [
    path("", AppointmentListCreateAPIView.as_view(), name="appointment-list-create"),
    path("<int:pk>/", AppointmentDetailAPIView.as_view(), name="appointment-detail"),
    
]