# patients/permissions.py
from rest_framework.permissions import BasePermission, SAFE_METHODS


def _is_admin(user):
    return hasattr(user, 'profile') and user.profile.role == 'admin'


def _can_edit_visit(user, visit):
    """
    Check if user can edit a visit.
    Rules:
    - Admin can edit any visit
    - Visit creator can edit their own visit
    - Legacy fallback: if visit.created_by is NULL, allow patient creator to edit
    """
    if _is_admin(user):
        return True

    # Normal rule: visit creator
    if visit.created_by_id is not None:
        return visit.created_by_id == user.id

    # Legacy fallback: patient creator (for visits with NULL created_by)
    patient_owner_id = getattr(visit.patient, "created_by_id", None)
    return patient_owner_id == user.id


class IsPatientOwnerOrAdmin(BasePermission):
    """
    For Patient objects.
    Read access: any authenticated user.
    Write access: only the patient's created_by user, or an admin.
    """

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        if _is_admin(request.user):
            return True
        return obj.created_by == request.user


class IsPatientFileOwnerOrAdmin(BasePermission):
    """
    For PatientFile objects.
    Read access: any authenticated user.
    Write access: only the patient's creator or admin.
    """

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        if _is_admin(request.user):
            return True
        return obj.patient.created_by == request.user


class IsVisitOwnerOrAdmin(BasePermission):
    """
    For Visit objects.
    Read access: any authenticated user.
    Write access: visit creator, or patient creator for legacy visits, or admin.
    """

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return _can_edit_visit(request.user, obj)


class IsVitalSignOwnerOrAdmin(BasePermission):
    """
    For VitalSign objects.
    Read access: any authenticated user.
    Write access: visit creator, or patient creator for legacy visits, or admin.
    VitalSigns inherit ownership from their parent Visit.
    """

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return _can_edit_visit(request.user, obj.visit)
