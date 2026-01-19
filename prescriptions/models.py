from django.db import models


class Medication(models.Model):
    name = models.CharField(max_length=150)
    form = models.CharField(max_length=50, blank=True, default="")       # tablet, syrup, injection
    strength = models.CharField(max_length=50, blank=True, default="")   # 500mg, 250mg/5ml
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name", "strength", "form"]

    def __str__(self):
        parts = [self.name]
        if self.strength:
            parts.append(self.strength)
        if self.form:
            parts.append(f"({self.form})")
        return " ".join(parts)


class PrescriptionTemplate(models.Model):
    name = models.CharField(max_length=150)
    name_fr = models.CharField(max_length=150, blank=True, default="")
    description = models.TextField(blank=True, default="")
    description_fr = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class PrescriptionTemplateItem(models.Model):
    template = models.ForeignKey(
        PrescriptionTemplate,
        on_delete=models.CASCADE,
        related_name="items",
    )
    medication = models.ForeignKey(Medication, on_delete=models.PROTECT)

    dosage = models.CharField(max_length=100, blank=True, default="")
    route = models.CharField(max_length=50, blank=True, default="")
    frequency = models.CharField(max_length=50, blank=True, default="")
    duration = models.CharField(max_length=50, blank=True, default="")
    instructions = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.template} - {self.medication}"


class Prescription(models.Model):
    visit = models.ForeignKey(
        "visits.Visit",
        on_delete=models.CASCADE,
        related_name="prescriptions",
    )

    # optional: remember if it came from a template
    template_used = models.ForeignKey(
        PrescriptionTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generated_prescriptions",
    )

    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Prescription #{self.id} (Visit #{self.visit_id})"


class PrescriptionItem(models.Model):
    prescription = models.ForeignKey(
        Prescription,
        on_delete=models.CASCADE,
        related_name="items",
    )

    medication = models.ForeignKey(
        Medication,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )

    dosage = models.CharField(max_length=100, blank=True, default="")
    route = models.CharField(max_length=50, blank=True, default="")
    frequency = models.CharField(max_length=50, blank=True, default="")
    duration = models.CharField(max_length=50, blank=True, default="")
    instructions = models.TextField(blank=True, default="")

    allow_outside_purchase = models.BooleanField(
        default=False,
        help_text="Allow patient to buy outside hospital if out of stock.",
    )

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.medication} (Prescription #{self.prescription_id})"
