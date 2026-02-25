from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import Group
from unfold.admin import ModelAdmin
from .models import Category, Transaction


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ("name", "type")
    list_filter = ("type",)
    search_fields = ("name",)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.is_superuser:
            return queryset
        return queryset.filter(owner=request.user)

    def get_list_display(self, request):
        base = list(super().get_list_display(request))
        if request.user.is_superuser and "owner" not in base:
            base.append("owner")
        return tuple(base)

    def get_list_filter(self, request):
        base = list(super().get_list_filter(request))
        if request.user.is_superuser and "owner" not in base:
            base.append("owner")
        return tuple(base)

    def get_exclude(self, request, obj=None):
        exclude = list(super().get_exclude(request, obj) or [])
        if not request.user.is_superuser:
            exclude.append("owner")
        return exclude

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser or not obj.owner_id:
            obj.owner = request.user
        super().save_model(request, obj, form, change)


@admin.register(Transaction)
class TransactionAdmin(ModelAdmin):
    list_display = ("category", "amount", "date", "created_at")
    list_filter = ("category", "date")
    search_fields = ("description",)
    ordering = ("-date",)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.is_superuser:
            return queryset
        return queryset.filter(owner=request.user)

    def get_list_display(self, request):
        base = list(super().get_list_display(request))
        if request.user.is_superuser and "owner" not in base:
            base.append("owner")
        return tuple(base)

    def get_list_filter(self, request):
        base = list(super().get_list_filter(request))
        if request.user.is_superuser and "owner" not in base:
            base.append("owner")
        return tuple(base)

    def get_exclude(self, request, obj=None):
        exclude = list(super().get_exclude(request, obj) or [])
        if not request.user.is_superuser:
            exclude.append("owner")
        return exclude

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "category" and not request.user.is_superuser:
            kwargs["queryset"] = Category.objects.filter(owner=request.user)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            if obj.category.owner_id != request.user.id:
                raise PermissionDenied("Category ownership mismatch.")
            obj.owner = request.user
        elif not obj.owner_id and obj.category_id:
            obj.owner = obj.category.owner
        super().save_model(request, obj, form, change)


User = get_user_model()


class UserAdmin(DjangoUserAdmin):
    def get_fieldsets(self, request, obj=None):
        if request.user.is_superuser:
            return super().get_fieldsets(request, obj)
        return (
            (None, {"fields": ("username", "password")}),
            ("Personal info", {"fields": ("first_name", "last_name", "email")}),
            ("Status", {"fields": ("is_active", "is_staff")}),
        )

    def get_add_fieldsets(self, request, obj=None):
        if request.user.is_superuser:
            return super().get_add_fieldsets(request, obj)
        return (
            (
                None,
                {
                    "classes": ("wide",),
                    "fields": (
                        "username",
                        "password1",
                        "password2",
                        "first_name",
                        "last_name",
                        "email",
                        "is_active",
                        "is_staff",
                    ),
                },
            ),
        )

    def has_change_permission(self, request, obj=None):
        if obj and obj.is_superuser and not request.user.is_superuser:
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if obj and obj.is_superuser and not request.user.is_superuser:
            return False
        return super().has_delete_permission(request, obj)

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            obj.is_superuser = False
        super().save_model(request, obj, form, change)
        if not request.user.is_superuser:
            obj.user_permissions.clear()
            obj.groups.clear()


class GroupAdmin(admin.ModelAdmin):
    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass

try:
    admin.site.unregister(Group)
except admin.sites.NotRegistered:
    pass

admin.site.register(User, UserAdmin)
admin.site.register(Group, GroupAdmin)
