import re
from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import UserProfile, DoctorAvailability

User = get_user_model()


def validate_password_strength(password):
    """
    Validate password meets security requirements:
    - At least 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character
    """
    errors = []

    if len(password) < 8:
        errors.append("Password must be at least 8 characters long.")

    if not re.search(r'[A-Z]', password):
        errors.append("Password must contain at least one uppercase letter.")

    if not re.search(r'[a-z]', password):
        errors.append("Password must contain at least one lowercase letter.")

    if not re.search(r'\d', password):
        errors.append("Password must contain at least one digit.")

    if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\\/~`]', password):
        errors.append("Password must contain at least one special character (!@#$%^&*(),.?\":{}|<>).")

    if errors:
        raise serializers.ValidationError(errors)

    return password


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile data."""

    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = UserProfile
        fields = [
            'role',
            'role_display',
            'phone',
            'specialization',
            'license_number',
            'department',
            'hire_date',
            'bio',
            'avatar',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class MeSerializer(serializers.ModelSerializer):
    """Serializer for the current user with profile data."""

    profile = UserProfileSerializer(read_only=True)
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'full_name',
            'is_staff',
            'is_active',
            'date_joined',
            'profile',
        ]
        read_only_fields = ['id', 'username', 'is_staff', 'is_active', 'date_joined']

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.username


class ProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user and profile data."""

    # User fields
    email = serializers.EmailField(required=False)
    first_name = serializers.CharField(max_length=150, required=False)
    last_name = serializers.CharField(max_length=150, required=False)

    # Profile fields
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    specialization = serializers.CharField(max_length=100, required=False, allow_blank=True)
    license_number = serializers.CharField(max_length=50, required=False, allow_blank=True)
    department = serializers.CharField(max_length=100, required=False, allow_blank=True)
    hire_date = serializers.DateField(required=False, allow_null=True)
    bio = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = User
        fields = [
            'email',
            'first_name',
            'last_name',
            'phone',
            'specialization',
            'license_number',
            'department',
            'hire_date',
            'bio',
        ]

    def update(self, instance, validated_data):
        # Update user fields
        user_fields = ['email', 'first_name', 'last_name']
        for field in user_fields:
            if field in validated_data:
                setattr(instance, field, validated_data.pop(field))
        instance.save()

        # Update profile fields
        profile = instance.profile
        profile_fields = ['phone', 'specialization', 'license_number', 'department', 'hire_date', 'bio']
        for field in profile_fields:
            if field in validated_data:
                setattr(profile, field, validated_data.pop(field))
        profile.save()

        return instance


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for password change."""

    current_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True)
    confirm_password = serializers.CharField(required=True, write_only=True)

    def validate_current_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate_new_password(self, value):
        """Validate new password meets security requirements."""
        return validate_password_strength(value)

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({
                'confirm_password': "New passwords do not match."
            })
        return data

    def save(self):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user


class DoctorAvailabilitySerializer(serializers.ModelSerializer):
    """Serializer for doctor availability slots."""

    slot_display = serializers.CharField(source='get_slot_display', read_only=True)

    class Meta:
        model = DoctorAvailability
        fields = [
            'id',
            'doctor',
            'date',
            'slot',
            'slot_display',
            'start_time',
            'end_time',
            'notes',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'doctor', 'created_at', 'updated_at']


class BulkAvailabilitySerializer(serializers.Serializer):
    """Serializer for bulk availability updates."""

    availabilities = serializers.ListField(
        child=serializers.DictField(),
        allow_empty=True
    )

    def validate_availabilities(self, value):
        for item in value:
            if 'date' not in item:
                raise serializers.ValidationError("Each availability must have a 'date' field.")
            if 'slot' not in item:
                raise serializers.ValidationError("Each availability must have a 'slot' field.")
            valid_slots = [choice[0] for choice in DoctorAvailability.SLOT_CHOICES]
            if item['slot'] not in valid_slots:
                raise serializers.ValidationError(f"Invalid slot: {item['slot']}. Must be one of {valid_slots}")
        return value
