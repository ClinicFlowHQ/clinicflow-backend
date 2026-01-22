from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsStaffOrReadOnly(BasePermission):
    """
    - Authenticated users can READ (GET/HEAD/OPTIONS)
    - Only staff can WRITE (POST/PATCH/PUT/DELETE)
    """
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return request.user and request.user.is_authenticated
        return request.user and request.user.is_authenticated and request.user.is_staff


class IsDoctorOnly(BasePermission):
    """
    - Authenticated users can READ (GET/HEAD/OPTIONS)
    - Only doctors can WRITE (POST/PATCH/PUT/DELETE)
    - Admins cannot create prescriptions (only doctors can prescribe)
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.method in SAFE_METHODS:
            return True

        # Only doctors can create/update/delete prescriptions
        try:
            return hasattr(request.user, 'profile') and request.user.profile.role == 'doctor'
        except Exception:
            return False


class IsAuthenticatedStaffRole(BasePermission):
    """
    - Authenticated users can READ (GET/HEAD/OPTIONS)
    - Doctors, Admins, and Nurses can WRITE (POST/PATCH/PUT/DELETE)
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.method in SAFE_METHODS:
            return True

        # Doctors, admins, and nurses can create/update/delete
        try:
            if hasattr(request.user, 'profile'):
                return request.user.profile.role in ['doctor', 'admin', 'nurse']
            return False
        except Exception:
            return False
