def can_view_users(request):
    return request.user.is_superuser or request.user.has_perm("auth.view_user")


def can_view_groups(request):
    return request.user.is_superuser or request.user.has_perm("auth.view_group")
