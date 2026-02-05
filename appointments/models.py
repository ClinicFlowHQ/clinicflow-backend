from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone


class Appointment(models.Model):
    STATUS_CHOICES = (
        ("SCHEDULED", "Scheduled"),
        ("CONFIRMED", "Confirmed"),
        ("CANCELLED", "Cancelled"),
        ("COMPLETED", "Completed"),
        ("NO_SHOW", "No-show"),
        ("RESCHEDULED", "Rescheduled"),
    )

    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.CASCADE,
        related_name="appointments",
    )

    # Doctor assigned to this appointment
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="appointments",
        help_text="Doctor assigned to this appointment",
    )

    # When
    scheduled_at = models.DateTimeField()

    # Lifecycle
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="SCHEDULED")

    # Optional notes
    reason = models.CharField(max_length=255, blank=True, default="")
    notes = models.TextField(blank=True, default="")

    # Optional: link appointment to a Visit once the patient is seen
    visit = models.OneToOneField(
        "visits.Visit",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="appointment",
    )

    # SMS reminder settings
    reminders_enabled = models.BooleanField(default=False)
    reminder_sent_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-scheduled_at"]
        indexes = [
            models.Index(fields=["scheduled_at"]),
            models.Index(fields=["status"]),
            # Optimise the daily reminder query
            models.Index(
                fields=["reminders_enabled", "reminder_sent_at", "scheduled_at", "status"],
                name="idx_reminder_query",
            ),
        ]

    def clean(self):
        # Prevent creating/updating to the past (except if already completed/cancelled)
        if self.scheduled_at and self.status in {"SCHEDULED", "CONFIRMED", "RESCHEDULED"}:
            if self.scheduled_at < timezone.now():
                raise ValidationError({"scheduled_at": "Appointment cannot be in the past."})

    def save(self, *args, **kwargs):
        self.full_clean()  # ensures clean() runs
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Appointment #{self.id} - {self.patient} - {self.scheduled_at:%Y-%m-%d %H:%M}"


class AppointmentSMSLog(models.Model):
    """
    Immutable log of every SMS send attempt for appointment reminders.
    One row per attempt — successful or failed.
    """

    STATUS_CHOICES = (
        ("SUCCESS", "Success"),
        ("FAILED", "Failed"),
    )

    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.CASCADE,
        related_name="sms_logs",
    )
    phone = models.CharField(max_length=30, help_text="E.164 phone number sent to")
    provider = models.CharField(max_length=30, default="africastalking")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    message_id = models.CharField(
        max_length=100, blank=True, default="",
        help_text="Provider message ID for delivery tracking",
    )
    error_message = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["appointment", "status"]),
        ]

    def __str__(self):
        return f"SMS {self.status} → {self.phone} (appt #{self.appointment_id})"