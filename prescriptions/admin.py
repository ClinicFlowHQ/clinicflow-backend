from django.contrib import admin
from .models import (
    Medication,
    PrescriptionTemplate,
    PrescriptionTemplateItem,
    Prescription,
    PrescriptionItem,
)


class PrescriptionTemplateItemInline(admin.TabularInline):
    model = PrescriptionTemplateItem
    extra = 1


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


@admin.register(Medication)
class MedicationAdmin(admin.ModelAdmin):
    list_display = ("name", "strength", "form", "is_active")
    search_fields = ("name", "strength", "form")
    list_filter = ("is_active",)


class PrescriptionItemInline(admin.TabularInline):
    model = PrescriptionItem
    extra = 0


@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = ("id", "visit", "template_used", "created_at")
    list_filter = ("created_at",)
    search_fields = ("id", "visit__id", "notes")
    inlines = [PrescriptionItemInline]
