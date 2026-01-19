from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import MeView, ProfileUpdateView, ChangePasswordView

urlpatterns = [
    path("login/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("refresh/", TokenRefreshView.as_view(), name="token_refresh_legacy"),  # Keep for backwards compatibility
    path("me/", MeView.as_view(), name="me"),
    path("profile/", ProfileUpdateView.as_view(), name="profile_update"),
    path("change-password/", ChangePasswordView.as_view(), name="change_password"),
]
