# prescriptions/serializers.py

from rest_framework import serializers
from .models import (
    Medication,
    Prescription,
    PrescriptionItem,
    PrescriptionTemplate,
    PrescriptionTemplateItem,
)


class MedicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Medication
        fields = ["id", "name", "form", "strength", "is_active"]


# -------- Items (WRITE) --------
class PrescriptionItemWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrescriptionItem
        fields = [
            "medication",
            "dosage",
            "route",
            "frequency",
            "duration",
            "instructions",
            "allow_outside_purchase",
        ]


# -------- Items (READ) --------
class PrescriptionItemReadSerializer(serializers.ModelSerializer):
    medication = MedicationSerializer()

    class Meta:
        model = PrescriptionItem
        fields = [
            "id",
            "medication",
            "dosage",
            "route",
            "frequency",
            "duration",
            "instructions",
            "allow_outside_purchase",
        ]


# -------- Prescription (LIST) --------
# Used for: GET /api/prescriptions/  (Option A UI)
# Shows patient name + visit number alongside each saved prescription.
class PrescriptionListSerializer(serializers.ModelSerializer):
    visit_id = serializers.IntegerField(source="visit.id", read_only=True)
    patient_id = serializers.IntegerField(source="visit.patient.id", read_only=True)
    patient_name = serializers.SerializerMethodField()

    class Meta:
        model = Prescription
        fields = [
            "id",
            "visit_id",
            "patient_id",
            "patient_name",
            "created_at",
            "updated_at",
        ]

    def get_patient_name(self, obj):
        patient = getattr(obj.visit, "patient", None)
        if not patient:
            return ""
        first = getattr(patient, "first_name", "") or ""
        last = getattr(patient, "last_name", "") or ""
        return f"{first} {last}".strip()


# -------- Prescription (WRITE) --------
class PrescriptionSerializer(serializers.ModelSerializer):
    items = PrescriptionItemWriteSerializer(many=True)

    class Meta:
        model = Prescription
        fields = [
            "id",
            "visit",
            "template_used",
            "notes",
            "items",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def create(self, validated_data):
        items_data = validated_data.pop("items", [])
        prescription = Prescription.objects.create(**validated_data)

        PrescriptionItem.objects.bulk_create(
            [PrescriptionItem(prescription=prescription, **item) for item in items_data]
        )
        return prescription

    def update(self, instance, validated_data):
        items_data = validated_data.pop("items", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if items_data is not None:
            instance.items.all().delete()
            PrescriptionItem.objects.bulk_create(
                [PrescriptionItem(prescription=instance, **item) for item in items_data]
            )

        return instance


# -------- Prescription (READ detail) --------
class PrescriptionDetailSerializer(serializers.ModelSerializer):
    items = PrescriptionItemReadSerializer(many=True)

    class Meta:
        model = Prescription
        fields = [
            "id",
            "visit",
            "template_used",
            "notes",
            "items",
            "created_at",
            "updated_at",
        ]


# -------- Templates (READ) --------
class PrescriptionTemplateItemReadSerializer(serializers.ModelSerializer):
    medication_display = serializers.SerializerMethodField()

    class Meta:
        model = PrescriptionTemplateItem
        fields = [
            "id",
            "medication",
            "medication_display",
            "dosage",
            "route",
            "frequency",
            "duration",
            "instructions",
        ]

    def get_medication_display(self, obj):
        parts = [obj.medication.name]
        if obj.medication.strength:
            parts.append(obj.medication.strength)
        if obj.medication.form:
            parts.append(obj.medication.form)
        return " ".join([p for p in parts if p])


class PrescriptionTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrescriptionTemplate
        fields = ["id", "name", "description", "is_active"]


class PrescriptionTemplateDetailSerializer(serializers.ModelSerializer):
    items = PrescriptionTemplateItemReadSerializer(many=True)

    class Meta:
        model = PrescriptionTemplate
        fields = ["id", "name", "description", "is_active", "items"]
