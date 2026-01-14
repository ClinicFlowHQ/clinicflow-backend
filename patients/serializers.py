# patients/serializers.py
from rest_framework import serializers
from .models import Patient


class PatientSerializer(serializers.ModelSerializer):
    # annotations (not DB fields) → read-only
    last_visit_date = serializers.DateTimeField(read_only=True)
    next_visit_date = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Patient
        fields = [
            "id",
            "patient_code",
            "first_name",
            "last_name",
            "sex",
            "date_of_birth",
            "phone",
            "address",
            "is_active",
            "created_at",
            "last_visit_date",
            "next_visit_date",
        ]
        read_only_fields = [
            "id",
            "patient_code",
            "created_at",
            "last_visit_date",
            "next_visit_date",
        ]
