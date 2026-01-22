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


# -------- Nested Patient (for prescription list/detail) --------
class PatientNestedSerializer(serializers.Serializer):
    """Lightweight nested patient for prescriptions."""
    id = serializers.IntegerField()
    patient_code = serializers.CharField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()


# -------- Prescription (LIST) --------
# Used for: GET /api/prescriptions/  (Option A UI)
# Shows patient name + visit number alongside each saved prescription.
class PrescriptionListSerializer(serializers.ModelSerializer):
    visit_id = serializers.SerializerMethodField()
    patient_id = serializers.SerializerMethodField()
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

    def get_visit_id(self, obj):
        return obj.visit.id if obj.visit else None

    def get_patient_id(self, obj):
        return obj.patient.id if obj.patient else None

    def get_patient_name(self, obj):
        patient = obj.patient
        if not patient:
            return ""
        first = getattr(patient, "first_name", "") or ""
        last = getattr(patient, "last_name", "") or ""
        return f"{first} {last}".strip()


# -------- Prescription (WRITE) --------
class PrescriptionSerializer(serializers.ModelSerializer):
    items = PrescriptionItemWriteSerializer(many=True)
    # Patient is required
    # Visit is optional (null=True, blank=True in model)
    visit = serializers.PrimaryKeyRelatedField(
        queryset=Prescription._meta.get_field('visit').related_model.objects.all(),
        required=False,
        allow_null=True
    )

    class Meta:
        model = Prescription
        fields = [
            "id",
            "patient",
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


# -------- Nested Visit (for prescription detail) --------
class VisitNestedSerializer(serializers.Serializer):
    """Lightweight nested visit for prescriptions."""
    id = serializers.IntegerField()
    visit_date = serializers.DateTimeField()
    visit_type = serializers.CharField()

    def to_representation(self, instance):
        if instance is None:
            return None
        return super().to_representation(instance)


# -------- Prescription (READ detail) --------
class PrescriptionDetailSerializer(serializers.ModelSerializer):
    items = PrescriptionItemReadSerializer(many=True)
    patient = PatientNestedSerializer(read_only=True)
    visit = VisitNestedSerializer(read_only=True, allow_null=True)

    class Meta:
        model = Prescription
        fields = [
            "id",
            "patient",
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
        fields = ["id", "name", "name_fr", "description", "description_fr", "is_active"]


class PrescriptionTemplateDetailSerializer(serializers.ModelSerializer):
    items = PrescriptionTemplateItemReadSerializer(many=True)

    class Meta:
        model = PrescriptionTemplate
        fields = ["id", "name", "name_fr", "description", "description_fr", "is_active", "items"]


# -------- Template Item (WRITE) --------
class PrescriptionTemplateItemWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrescriptionTemplateItem
        fields = [
            "medication",
            "dosage",
            "route",
            "frequency",
            "duration",
            "instructions",
        ]


# -------- Template (WRITE) --------
class PrescriptionTemplateWriteSerializer(serializers.ModelSerializer):
    items = PrescriptionTemplateItemWriteSerializer(many=True, required=False)

    class Meta:
        model = PrescriptionTemplate
        fields = ["id", "name", "name_fr", "description", "description_fr", "is_active", "items"]
        read_only_fields = ["id"]

    def create(self, validated_data):
        items_data = validated_data.pop("items", [])
        template = PrescriptionTemplate.objects.create(**validated_data)

        PrescriptionTemplateItem.objects.bulk_create(
            [PrescriptionTemplateItem(template=template, **item) for item in items_data]
        )
        return template

    def update(self, instance, validated_data):
        items_data = validated_data.pop("items", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if items_data is not None:
            instance.items.all().delete()
            PrescriptionTemplateItem.objects.bulk_create(
                [PrescriptionTemplateItem(template=instance, **item) for item in items_data]
            )
        return instance
