"""URL configuration for accounts admin views."""
from django.urls import path

from apps.accounts.views.admin_views import (
    PermissionMatrixView,
    RoleCreateView,
    RoleDetailView,
    RoleListView,
    RoleUpdateView,
    UserCreateView,
    UserDetailView,
    UserListView,
    UserRoleAssignView,
    UserRoleHistoryView,
    UserRoleRevokeView,
    UserToggleActiveView,
    UserUpdateView,
)

app_name = "accounts_admin"

urlpatterns = [
    # User management
    path("users/", UserListView.as_view(), name="user_list"),
    path("users/crear/", UserCreateView.as_view(), name="user_create"),
    path("users/<uuid:pk>/", UserDetailView.as_view(), name="user_detail"),
    path("users/<uuid:pk>/editar/", UserUpdateView.as_view(), name="user_update"),
    path("users/<uuid:pk>/edit/", UserUpdateView.as_view(), name="user_edit"),
    path("users/<uuid:pk>/toggle/", UserToggleActiveView.as_view(), name="user_toggle"),
    path("users/<uuid:pk>/roles/", UserRoleAssignView.as_view(), name="user_roles"),
    path("users/<uuid:pk>/roles/<uuid:role_id>/revocar/", UserRoleRevokeView.as_view(), name="user_role_revoke"),
    path("users/<uuid:pk>/roles/history/", UserRoleHistoryView.as_view(), name="user_role_history"),

    # Role management
    path("roles/", RoleListView.as_view(), name="role_list"),
    path("roles/crear/", RoleCreateView.as_view(), name="role_create"),
    path("roles/<uuid:pk>/", RoleDetailView.as_view(), name="role_detail"),
    path("roles/<uuid:pk>/editar/", RoleUpdateView.as_view(), name="role_update"),
    path("roles/<uuid:pk>/edit/", RoleUpdateView.as_view(), name="role_edit"),

    # Permission matrix
    path("permisos/", PermissionMatrixView.as_view(), name="permission_matrix"),
]
