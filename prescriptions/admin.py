from django.contrib import admin
from .models import (
    Medication,
    PrescriptionTemplate,
    PrescriptionTemplateItem,
    Prescription,
    PrescriptionItem,
)


@admin.register(Medication)
class MedicationAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "strength", "form", "is_active")
    list_filter = ("is_active", "form")
    search_fields = ("name", "strength", "form")


class PrescriptionTemplateItemInline(admin.TabularInline):
    model = PrescriptionTemplateItem
    extra = 1
    autocomplete_fields = ["medication"]


@admin.register(PrescriptionTemplate)
class PrescriptionTemplateAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "name_fr", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "name_fr")
    fieldsets = (
        (None, {
            "fields": ("name", "description", "is_active")
        }),
        ("French / Français", {
            "fields": ("name_fr", "description_fr"),
            "classes": ("collapse",),
        }),
    )
    inlines = [PrescriptionTemplateItemInline]


class PrescriptionItemInline(admin.TabularInline):
    model = PrescriptionItem
    extra = 1
    autocomplete_fields = ["medication"]


@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = ("id", "visit", "template_used", "created_at")
    list_filter = ("created_at", "template_used")
    search_fields = ("visit__patient__first_name", "visit__patient__last_name")
    inlines = [PrescriptionItemInline]
