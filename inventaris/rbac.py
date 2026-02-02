from __future__ import annotations

from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied

ROLE_ADMIN = "Admin"
ROLE_SARPRAS = "Staff Sarpras"
ROLE_KEPSEK = "Kepala Sekolah"

ALL_ROLES = (ROLE_ADMIN, ROLE_SARPRAS, ROLE_KEPSEK)


def user_in_roles(user, roles: tuple[str, ...]) -> bool:
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return Group.objects.filter(user=user, name__in=roles).exists()


def require_roles(user, roles: tuple[str, ...]):
    if not user_in_roles(user, roles):
        raise PermissionDenied
