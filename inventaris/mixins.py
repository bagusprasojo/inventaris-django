from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied

from .rbac import user_in_roles


class RoleRequiredMixin(LoginRequiredMixin):
    allowed_roles: tuple[str, ...] = ()

    def dispatch(self, request, *args, **kwargs):
        if self.allowed_roles and not user_in_roles(request.user, self.allowed_roles):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)
