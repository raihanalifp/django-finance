from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import Group, Permission
from django.contrib.auth.password_validation import validate_password
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
        if request.user.is_superuser:
            return (OwnerScopeFilter, "owner", "category", "date")
        return ("category", "date")

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


class OwnerScopeFilter(admin.SimpleListFilter):
    title = "scope"
    parameter_name = "scope"

    def lookups(self, request, model_admin):
        if request.user.is_superuser:
            return (("mine", "My transactions"), ("all", "All transactions"))
        return ()

    def queryset(self, request, queryset):
        if not request.user.is_superuser:
            return queryset
        if request.GET.get("owner__id__exact"):
            return queryset
        value = self.value()
        if value == "all":
            return queryset
        return queryset.filter(owner=request.user)


User = get_user_model()


class LooseUserCreationForm(UserCreationForm):
    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise ValidationError(self.error_messages["password_mismatch"], code="password_mismatch")
        return password2

    def validate_password_for_user(self, user, **kwargs):
        return


class UserAdmin(DjangoUserAdmin):
    show_add_link = True
    add_form = LooseUserCreationForm

    def get_fieldsets(self, request, obj=None):
        if obj is None:
            return self.get_add_fieldsets(request, obj)
        if request.user.is_superuser:
            return super().get_fieldsets(request, obj)
        return (
            (None, {"fields": ("username", "password")}),
            ("Personal info", {"fields": ("first_name", "last_name", "email")}),
            ("Status", {"fields": ("is_active", "is_staff")}),
        )

    def get_add_fieldsets(self, request, obj=None):
        if request.user.is_superuser:
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
                            "is_superuser",
                            "groups",
                            "user_permissions",
                        ),
                    },
                ),
            )
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
        is_superuser_request = request.user.is_superuser
        creating = obj.pk is None
        if not is_superuser_request:
            obj.is_superuser = False
            if creating and not obj.is_staff:
                obj.is_staff = True
        super().save_model(request, obj, form, change)
        if creating and not obj.is_superuser and obj.is_staff:
            messages.info(
                request,
                "User dibuat sebagai staff agar bisa login ke admin.",
            )
        if creating:
            raw_password = form.cleaned_data.get("password1")
            if raw_password:
                try:
                    validate_password(raw_password, obj)
                except ValidationError as exc:
                    messages.warning(
                        request,
                        "Password lemah: "
                        + " ".join(exc.messages)
                        + " User tetap dibuat, tetapi disarankan mengganti password.",
                    )
        if not obj.is_superuser:
            default_codenames = [
                "add_category",
                "change_category",
                "delete_category",
                "view_category",
                "add_transaction",
                "change_transaction",
                "delete_transaction",
                "view_transaction",
            ]
            default_perms = Permission.objects.filter(
                content_type__app_label="transactions",
                codename__in=default_codenames,
            )
            if is_superuser_request:
                if creating:
                    obj.user_permissions.add(*default_perms)
            else:
                obj.user_permissions.set(default_perms)
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
