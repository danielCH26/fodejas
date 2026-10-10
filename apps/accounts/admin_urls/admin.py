"""URL configuration for accounts admin views."""

from django.urls import path

from apps.accounts.views import admin_views

app_name = "accounts_admin"

urlpatterns = [
    # User management
    path("users/", admin_views.UserListView.as_view(), name="user_list"),
    path("users/crear/", admin_views.UserCreateView.as_view(), name="user_create"),
    path("users/<uuid:pk>/", admin_views.UserDetailView.as_view(), name="user_detail"),
    path("users/<uuid:pk>/editar/", admin_views.UserUpdateView.as_view(), name="user_update"),
    path("users/<uuid:pk>/toggle/", admin_views.UserToggleActiveView.as_view(), name="user_toggle"),
    path("users/<uuid:pk>/roles/", admin_views.UserRoleAssignView.as_view(), name="user_roles"),
    path(
        "users/<uuid:pk>/roles/<int:role_id>/revocar/",
        admin_views.UserRoleRevokeView.as_view(),
        name="user_role_revoke",
    ),
    # Role management
    path("roles/", admin_views.RoleListView.as_view(), name="role_list"),
    path("roles/crear/", admin_views.RoleCreateView.as_view(), name="role_create"),
    path("roles/<int:pk>/", admin_views.RoleDetailView.as_view(), name="role_detail"),
    path("roles/<int:pk>/editar/", admin_views.RoleUpdateView.as_view(), name="role_update"),
]
