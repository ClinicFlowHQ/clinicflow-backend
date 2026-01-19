from django.db import models
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

User = get_user_model()


class UserProfile(models.Model):
    """Extended user profile with role-based access control."""

    ROLE_CHOICES = [
        ('admin', 'Administrator'),
        ('doctor', 'Doctor'),
        ('nurse', 'Nurse'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='nurse'
    )
    phone = models.CharField(max_length=20, blank=True)
    specialization = models.CharField(
        max_length=100,
        blank=True,
        help_text="For doctors: medical specialty (e.g., Cardiology, Pediatrics)"
    )
    license_number = models.CharField(
        max_length=50,
        blank=True,
        help_text="Medical license or registration number"
    )
    department = models.CharField(max_length=100, blank=True)
    hire_date = models.DateField(null=True, blank=True)
    bio = models.TextField(blank=True)
    avatar = models.ImageField(
        upload_to='avatars/',
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"

    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"

    @property
    def full_name(self):
        return f"{self.user.first_name} {self.user.last_name}".strip() or self.user.username

    @property
    def is_admin(self):
        return self.role == 'admin'

    @property
    def is_doctor(self):
        return self.role == 'doctor'

    @property
    def is_nurse(self):
        return self.role == 'nurse'


# Signal to auto-create profile when user is created
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        # Determine role based on user status
        role = 'admin' if instance.is_superuser else 'nurse'
        UserProfile.objects.create(user=instance, role=role)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    # Ensure profile exists
    if not hasattr(instance, 'profile'):
        role = 'admin' if instance.is_superuser else 'nurse'
        UserProfile.objects.create(user=instance, role=role)
