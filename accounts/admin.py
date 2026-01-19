from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model
from .models import UserProfile

User = get_user_model()


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'
    fk_name = 'user'


class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'get_role', 'is_staff')
    list_select_related = ('profile',)

    def get_role(self, instance):
        return instance.profile.get_role_display() if hasattr(instance, 'profile') else '-'
    get_role.short_description = 'Role'

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return list()
        return super().get_inline_instances(request, obj)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'phone', 'department', 'created_at')
    list_filter = ('role', 'department')
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name', 'phone')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Role & Department', {
            'fields': ('role', 'department')
        }),
        ('Professional Info', {
            'fields': ('specialization', 'license_number', 'hire_date')
        }),
        ('Contact', {
            'fields': ('phone',)
        }),
        ('Additional', {
            'fields': ('bio', 'avatar')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
