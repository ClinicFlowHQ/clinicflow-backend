# visits/serializers.py
from rest_framework import serializers
from .models import Visit, VitalSign


class VitalSignSerializer(serializers.ModelSerializer):
    class Meta:
        model = VitalSign
        fields = [
            "id",
            "visit",
            "measured_at",
            "weight_kg",
            "height_cm",
            "temperature_c",
            "bp_systolic",
            "bp_diastolic",
            "heart_rate_bpm",
            "respiratory_rate_rpm",
            "oxygen_saturation_pct",
            "head_circumference_cm",
            "notes",
        ]
        read_only_fields = ["id"]


class VisitSerializer(serializers.ModelSerializer):
    vital_signs = VitalSignSerializer(many=True, read_only=True)

    # ✅ Added for dropdown labels
    patient_name = serializers.SerializerMethodField()

    # ✅ Added for ownership check (returns user ID)
    created_by = serializers.PrimaryKeyRelatedField(read_only=True)

    # ✅ Added for legacy visit fallback (patient's creator ID)
    patient_created_by = serializers.SerializerMethodField()

    def get_patient_name(self, obj):
        p = getattr(obj, "patient", None)
        if not p:
            return None
        fn = getattr(p, "first_name", "") or ""
        ln = getattr(p, "last_name", "") or ""
        name = f"{fn} {ln}".strip()
        return name or None

    def get_patient_created_by(self, obj):
        p = getattr(obj, "patient", None)
        if not p:
            return None
        return getattr(p, "created_by_id", None)

    class Meta:
        model = Visit
        fields = [
            "id",
            "patient",
            "patient_name",       # ✅ added
            "created_by",         # ✅ added for ownership check
            "patient_created_by", # ✅ added for legacy fallback
            "visit_date",
            "visit_type",
            "chief_complaint",
            "medical_history",
            "history_of_present_illness",
            "physical_exam",
            "complementary_exam",
            "assessment",
            "plan",
            "treatment",
            "notes",
            "vital_signs",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at", "vital_signs"]
