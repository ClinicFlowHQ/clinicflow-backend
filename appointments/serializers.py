from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from .models import Appointment
from patients.models import Patient

User = get_user_model()


class PatientSerializer(serializers.ModelSerializer):
    """Minimal serializer for patient info in appointments."""
    class Meta:
        model = Patient
        fields = ["id", "patient_code", "first_name", "last_name", "phone"]


class DoctorSerializer(serializers.ModelSerializer):
    """Minimal serializer for doctor info in appointments."""
    full_name = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "full_name", "role"]

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.username

    def get_role(self, obj):
        if hasattr(obj, 'profile'):
            return obj.profile.role
        return None


class AppointmentSerializer(serializers.ModelSerializer):
    """
    Appointment serializer with SMS reminder fields.

    Reminder behavior:
    - reminders_enabled: User can toggle ON/OFF at any time
    - reminder_sent_at: Read-only timestamp of when SMS was sent

    When user toggles reminders_enabled ON after SMS was already sent,
    reminder_sent_at is NOT cleared (no duplicate SMS). The cron job
    only sends SMS if reminders_enabled=True AND reminder_sent_at IS NULL.

    To "reset" and allow re-sending, admin must clear reminder_sent_at manually.
    """
    doctor_details = DoctorSerializer(source='doctor', read_only=True)
    patient = PatientSerializer(read_only=True)
    patient_id = serializers.PrimaryKeyRelatedField(
        queryset=Patient.objects.all(),
        source='patient',
        write_only=True
    )

    class Meta:
        model = Appointment
        fields = [
            "id",
            "patient",
            "patient_id",
            "doctor",
            "doctor_details",
            "scheduled_at",
            "status",
            "reason",
            "notes",
            "visit",
            "reminders_enabled",
            "reminder_sent_at",  # Read-only: shows when SMS was sent
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "reminder_sent_at", "created_at", "updated_at"]

    def create(self, validated_data):
        try:
            return super().create(validated_data)
        except DjangoValidationError as e:
            raise serializers.ValidationError(e.message_dict if hasattr(e, 'message_dict') else str(e))

    def update(self, instance, validated_data):
        try:
            return super().update(instance, validated_data)
        except DjangoValidationError as e:
            raise serializers.ValidationError(e.message_dict if hasattr(e, 'message_dict') else str(e))
