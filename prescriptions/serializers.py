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
            "medication",  # FK id
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


# -------- Nested Visit (for prescription detail) --------
class VisitNestedSerializer(serializers.Serializer):
    """Lightweight nested visit for prescriptions."""
    id = serializers.IntegerField()
    visit_date = serializers.DateTimeField()
    visit_type = serializers.CharField()
    patient = serializers.SerializerMethodField()

    def get_patient(self, obj):
        p = obj.patient
        return {
            "id": p.id,
            "patient_code": p.patient_code,
            "first_name": p.first_name,
            "last_name": p.last_name,
        }


# -------- Prescription (READ detail) --------
class PrescriptionDetailSerializer(serializers.ModelSerializer):
    items = PrescriptionItemReadSerializer(many=True)
    visit = VisitNestedSerializer(read_only=True)

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
