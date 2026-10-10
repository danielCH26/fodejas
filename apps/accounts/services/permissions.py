"""Permissions services with caching."""

from django.core.cache import cache

from apps.accounts.models import CustomUser


def get_user_effective_permissions(user: CustomUser) -> set:
    """
    Get all effective permissions for a user with caching.

    This returns the union of:
    - User's direct permissions (user.user_permissions)
    - Permissions from all groups the user belongs to (user.get_group_permissions())

    Args:
        user: The user to get permissions for

    Returns:
        Set of permission strings in format "app_label.codename"
    """
    cache_key = f"user_permissions_{user.id}"
    cached_perms = cache.get(cache_key)

    if cached_perms is not None:
        # Return cached permissions as a set
        return set(cached_perms)

    # Compute permissions
    permissions = user.get_all_permissions()

    # Cache for 5 minutes (300 seconds)
    cache.set(cache_key, list(permissions), timeout=300)

    return permissions


def invalidate_user_permissions_cache(user: CustomUser):
    """
    Invalidate the permissions cache for a user.

    Call this when user's roles or groups change.

    Args:
        user: The user whose cache to invalidate
    """
    cache_key = f"user_permissions_{user.id}"
    cache.delete(cache_key)
