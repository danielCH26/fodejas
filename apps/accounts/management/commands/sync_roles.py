"""Management command to sync roles and permissions with Django auth system."""

from django.core.management.base import BaseCommand

from apps.accounts.models import Permission, Role, RolePermission
from apps.accounts.services.sync import sync_permission_to_auth_perm, sync_role_to_group


class Command(BaseCommand):
    help = "Sync roles to Django groups and permissions to Django auth permissions"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be synced without making changes",
        )

    def handle(self, *args, **options):
        dry_run = options.get("dry_run", False)
        verbosity = options.get("verbosity", 1)

        roles_synced = 0
        permissions_synced = 0
        role_perms_synced = 0

        # Sync roles to groups
        self.stdout.write("\n=== Syncing Roles to Groups ===")
        roles = Role.objects.all()
        for role in roles:
            if dry_run:
                if role.group is None:
                    self.stdout.write(
                        f"  [DRY-RUN] Would create group '{role.code}' for role '{role.name}'"
                    )
                    roles_synced += 1
            else:
                try:
                    group = sync_role_to_group(role)
                    if verbosity > 1:
                        self.stdout.write(f"  Synced role '{role.name}' -> group '{group.name}'")
                    roles_synced += 1
                except Exception as e:
                    self.stderr.write(f"  ERROR syncing role '{role.name}': {e}")

        # Sync permissions to auth permissions
        self.stdout.write("\n=== Syncing Permissions to Django Auth ===")
        permissions = Permission.objects.all()
        for perm in permissions:
            if dry_run:
                if perm.auth_permission is None:
                    self.stdout.write(
                        f"  [DRY-RUN] Would create auth permission '{perm.action}' for '{perm.app_label}'"
                    )
                    permissions_synced += 1
            else:
                try:
                    auth_perm = sync_permission_to_auth_perm(perm)
                    if verbosity > 1:
                        self.stdout.write(
                            f"  Synced permission '{perm.action}' -> auth permission '{auth_perm.codename}'"
                        )
                    permissions_synced += 1
                except Exception as e:
                    self.stderr.write(f"  ERROR syncing permission '{perm.action}': {e}")

        # Sync role permissions to group permissions
        self.stdout.write("\n=== Syncing Role Permissions to Groups ===")
        role_perms = RolePermission.objects.select_related(
            "role__group", "permission__auth_permission"
        )

        for rp in role_perms:
            if rp.role.group is None:
                if verbosity > 1:
                    self.stdout.write(f"  SKIP: Role '{rp.role.name}' has no group yet")
                continue

            if rp.permission.auth_permission is None:
                if verbosity > 1:
                    self.stdout.write(
                        f"  SKIP: Permission '{rp.permission.action}' has no auth_permission yet"
                    )
                continue

            if dry_run:
                self.stdout.write(
                    f"  [DRY-RUN] Would add permission '{rp.permission.action}' to group '{rp.role.group.name}'"
                )
                role_perms_synced += 1
            else:
                try:
                    rp.role.group.permissions.add(rp.permission.auth_permission)
                    if verbosity > 1:
                        self.stdout.write(
                            f"  Added '{rp.permission.action}' to group '{rp.role.group.name}'"
                        )
                    role_perms_synced += 1
                except Exception as e:
                    self.stderr.write(f"  ERROR syncing role permission: {e}")

        # Summary
        self.stdout.write("\n" + "=" * 40)
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"[DRY-RUN] Would sync: {roles_synced} roles, {permissions_synced} permissions, {role_perms_synced} role-permissions"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Synced: {roles_synced} roles, {permissions_synced} permissions, {role_perms_synced} role-permissions"
                )
            )
