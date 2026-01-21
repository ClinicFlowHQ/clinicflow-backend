from datetime import datetime
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import DoctorAvailability
from .serializers import (
    MeSerializer, ProfileUpdateSerializer, ChangePasswordSerializer,
    DoctorAvailabilitySerializer, BulkAvailabilitySerializer
)


class MeView(APIView):
    """Get current user data with profile."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(MeSerializer(request.user).data)


class ProfileUpdateView(APIView):
    """Update current user's profile."""
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        serializer = ProfileUpdateSerializer(
            request.user,
            data=request.data,
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            # Return updated user data
            return Response(MeSerializer(request.user).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChangePasswordView(APIView):
    """Change current user's password."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={'request': request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'Password changed successfully.'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MyAvailabilityView(APIView):
    """Get and set current user's availability."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get availability for a month. Query params: year, month"""
        year = request.query_params.get('year')
        month = request.query_params.get('month')

        availabilities = DoctorAvailability.objects.filter(doctor=request.user)

        if year and month:
            try:
                year = int(year)
                month = int(month)
                availabilities = availabilities.filter(
                    date__year=year,
                    date__month=month
                )
            except ValueError:
                pass

        serializer = DoctorAvailabilitySerializer(availabilities, many=True)
        return Response(serializer.data)

    def post(self, request):
        """Create or update a single availability."""
        date_str = request.data.get('date')
        slot = request.data.get('slot', 'full_day')
        notes = request.data.get('notes', '')
        start_time = request.data.get('start_time')
        end_time = request.data.get('end_time')

        if not date_str:
            return Response(
                {'error': 'Date is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'error': 'Invalid date format. Use YYYY-MM-DD.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        availability, created = DoctorAvailability.objects.update_or_create(
            doctor=request.user,
            date=date,
            defaults={
                'slot': slot,
                'notes': notes,
                'start_time': start_time,
                'end_time': end_time,
            }
        )

        serializer = DoctorAvailabilitySerializer(availability)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )

    def delete(self, request):
        """Delete availability for a specific date."""
        date_str = request.query_params.get('date')

        if not date_str:
            return Response(
                {'error': 'Date is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'error': 'Invalid date format. Use YYYY-MM-DD.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        deleted, _ = DoctorAvailability.objects.filter(
            doctor=request.user,
            date=date
        ).delete()

        if deleted:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(
            {'error': 'No availability found for this date.'},
            status=status.HTTP_404_NOT_FOUND
        )


class BulkAvailabilityView(APIView):
    """Bulk update availability for multiple dates."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Set availability for multiple dates at once.
        Body: { "availabilities": [{"date": "2024-01-15", "slot": "morning", "notes": ""}, ...] }
        """
        serializer = BulkAvailabilitySerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        availabilities_data = serializer.validated_data['availabilities']
        results = []

        for item in availabilities_data:
            try:
                date = datetime.strptime(item['date'], '%Y-%m-%d').date()
            except ValueError:
                continue

            availability, created = DoctorAvailability.objects.update_or_create(
                doctor=request.user,
                date=date,
                defaults={
                    'slot': item['slot'],
                    'notes': item.get('notes', ''),
                    'start_time': item.get('start_time'),
                    'end_time': item.get('end_time'),
                }
            )
            results.append(DoctorAvailabilitySerializer(availability).data)

        return Response({'updated': len(results), 'availabilities': results})


class DoctorAvailabilityPublicView(APIView):
    """Get a specific doctor's availability (for scheduling appointments)."""
    permission_classes = [IsAuthenticated]

    def get(self, request, doctor_id):
        """Get availability for a specific doctor. Query params: year, month"""
        year = request.query_params.get('year')
        month = request.query_params.get('month')

        availabilities = DoctorAvailability.objects.filter(doctor_id=doctor_id)

        if year and month:
            try:
                year = int(year)
                month = int(month)
                availabilities = availabilities.filter(
                    date__year=year,
                    date__month=month
                )
            except ValueError:
                pass

        serializer = DoctorAvailabilitySerializer(availabilities, many=True)
        return Response(serializer.data)
