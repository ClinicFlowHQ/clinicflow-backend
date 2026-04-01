from django.conf import settings
from django.db import models
from django.utils import timezone


class Visit(models.Model):
    # Core link
    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.CASCADE,
        related_name="visits",
    )

    # Owner (doctor who created this visit)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="visits",
        null=True,  # Allow null for existing records
        blank=True,
    )

    # When / what type
    visit_date = models.DateTimeField(default=timezone.now)
    VISIT_TYPES = (
        ("CONSULTATION", "Consultation"),
        ("FOLLOW_UP", "Follow-up"),
    )
    visit_type = models.CharField(max_length=20, choices=VISIT_TYPES, default="CONSULTATION")

    # Medical content (doctor notes)
    chief_complaint = models.CharField(max_length=255, blank=True, default="")
    medical_history = models.TextField(blank=True, default="")  # before HPI
    history_of_present_illness = models.TextField(blank=True, default="")
    physical_exam = models.TextField(blank=True, default="")
    complementary_exam = models.TextField(blank=True, default="")  # after physical exam
    assessment = models.TextField(blank=True, default="")  # diagnosis / impressions
    plan = models.TextField(blank=True, default="")        # treatment plan
    treatment = models.TextField(blank=True, default="")   # treatment details
    notes = models.TextField(blank=True, default="")

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-visit_date"]

    def __str__(self):
        return f"Visit #{self.id} - {self.patient} - {self.visit_date:%Y-%m-%d}"


class VitalSign(models.Model):
    """
    We allow multiple vital-sign measurements per visit (e.g., at arrival + later).
    """
    visit = models.ForeignKey(Visit, on_delete=models.CASCADE, related_name="vital_signs")
    measured_at = models.DateTimeField(default=timezone.now)

    # Common vitals (all optional)
    weight_kg = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    height_cm = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    temperature_c = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)

    bp_systolic = models.PositiveSmallIntegerField(null=True, blank=True)
    bp_diastolic = models.PositiveSmallIntegerField(null=True, blank=True)

    heart_rate_bpm = models.PositiveSmallIntegerField(null=True, blank=True)
    respiratory_rate_rpm = models.PositiveSmallIntegerField(null=True, blank=True)
    oxygen_saturation_pct = models.PositiveSmallIntegerField(null=True, blank=True)

    # Pediatric-specific
    head_circumference_cm = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)

    notes = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ["-measured_at"]

    def __str__(self):
        return f"Vitals #{self.id} (Visit #{self.visit_id})"