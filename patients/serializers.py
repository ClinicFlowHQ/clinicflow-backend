# patients/serializers.py
from rest_framework import serializers
from .models import Patient, PatientFile


# Allowed file types for upload
ALLOWED_FILE_TYPES = [
    'application/pdf',
    'image/jpeg',
    'image/png',
    'image/gif',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
]

# Max file size: 10MB
MAX_FILE_SIZE = 10 * 1024 * 1024


class PatientFileSerializer(serializers.ModelSerializer):
    file = serializers.FileField(write_only=True)
    file_url = serializers.SerializerMethodField(read_only=True)
    uploaded_by_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = PatientFile
        fields = [
            'id',
            'patient',
            'file',
            'file_url',
            'original_filename',
            'file_size',
            'file_type',
            'category',
            'description',
            'uploaded_by',
            'uploaded_by_name',
            'uploaded_at',
        ]
        read_only_fields = [
            'id',
            'patient',
            'original_filename',
            'file_size',
            'file_type',
            'uploaded_by',
            'uploaded_by_name',
            'uploaded_at',
        ]

    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return None

    def get_uploaded_by_name(self, obj):
        if obj.uploaded_by:
            name = f"{obj.uploaded_by.first_name} {obj.uploaded_by.last_name}".strip()
            return name or obj.uploaded_by.username
        return None

    def validate_file(self, value):
        # Check file size
        if value.size > MAX_FILE_SIZE:
            raise serializers.ValidationError(
                f"File size must be less than {MAX_FILE_SIZE // (1024 * 1024)}MB."
            )

        # Check file type
        if value.content_type not in ALLOWED_FILE_TYPES:
            raise serializers.ValidationError(
                f"File type '{value.content_type}' is not allowed. "
                f"Allowed types: PDF, JPEG, PNG, GIF, DOC, DOCX."
            )

        return value

    def create(self, validated_data):
        file = validated_data.get('file')
        validated_data['original_filename'] = file.name
        validated_data['file_size'] = file.size
        validated_data['file_type'] = file.content_type
        validated_data['uploaded_by'] = self.context['request'].user
        return super().create(validated_data)


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
