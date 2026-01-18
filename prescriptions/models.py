from django.db import models
from visits.models import Visit


class Medication(models.Model):
    name = models.CharField(max_length=120)
    form = models.CharField(max_length=80, blank=True)
    strength = models.CharField(max_length=80, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        parts = [self.name]
        if self.strength:
            parts.append(self.strength)
        if self.form:
            parts.append(self.form)
        return " ".join(parts)


class PrescriptionTemplate(models.Model):
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class PrescriptionTemplateItem(models.Model):
    template = models.ForeignKey(
        PrescriptionTemplate, related_name="items", on_delete=models.CASCADE
    )
    medication = models.ForeignKey(Medication, on_delete=models.PROTECT)

    dosage = models.CharField(max_length=120, blank=True)
    route = models.CharField(max_length=80, blank=True)
    frequency = models.CharField(max_length=80, blank=True)
    duration = models.CharField(max_length=80, blank=True)
    instructions = models.TextField(blank=True)

    def __str__(self):
        return f"{self.template.name} - {self.medication}"


class Prescription(models.Model):
    visit = models.ForeignKey(Visit, related_name="prescriptions", on_delete=models.CASCADE)
    template_used = models.ForeignKey(
        PrescriptionTemplate, null=True, blank=True, on_delete=models.SET_NULL
    )
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Rx #{self.pk} (Visit {self.visit_id})"


class PrescriptionItem(models.Model):
    prescription = models.ForeignKey(
        Prescription, related_name="items", on_delete=models.CASCADE
    )
    medication = models.ForeignKey(Medication, on_delete=models.PROTECT)

    dosage = models.CharField(max_length=120, blank=True)
    route = models.CharField(max_length=80, blank=True)
    frequency = models.CharField(max_length=80, blank=True)
    duration = models.CharField(max_length=80, blank=True)
    instructions = models.TextField(blank=True)
    allow_outside_purchase = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.medication} for Rx #{self.prescription_id}"
