from __future__ import annotations

from django.apps import apps
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

from inventaris.rbac import ROLE_ADMIN, ROLE_SARPRAS, ROLE_KEPSEK


class Command(BaseCommand):
    help = "Create/update role groups and assign permissions"

    def handle(self, *args, **options):
        inventaris_models = [
            model for model in apps.get_models() if model._meta.app_label == "inventaris"
        ]

        def perms_for(model, actions):
            perms = []
            for action in actions:
                codename = f"{action}_{model._meta.model_name}"
                try:
                    perms.append(Permission.objects.get(codename=codename))
                except Permission.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(f"Permission not found: {codename}")
                    )
            return perms

        roles = {
            ROLE_ADMIN: {"actions": ("add", "change", "delete", "view")},
            ROLE_SARPRAS: {"actions": ("add", "change", "view")},
            ROLE_KEPSEK: {"actions": ("view",)},
        }

        for role_name, cfg in roles.items():
            group, _ = Group.objects.get_or_create(name=role_name)
            group.permissions.clear()
            actions = cfg["actions"]
            perms = []
            for model in inventaris_models:
                perms.extend(perms_for(model, actions))
            group.permissions.add(*perms)
            self.stdout.write(self.style.SUCCESS(f"Role {role_name} updated."))
