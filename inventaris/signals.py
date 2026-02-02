from __future__ import annotations

from django.db.models.signals import m2m_changed, post_save, pre_save
from django.dispatch import receiver

from .middleware import get_current_user
from .models import Asset, AuditLog


def _log_asset_change(asset: Asset, changes: dict[str, dict]):
    if not changes:
        return
    user = get_current_user()
    performed_by = user if user and user.is_authenticated else asset.updated_by or asset.created_by
    if performed_by is None:
        return
    AuditLog.objects.create(
        entity="asset",
        entity_id=asset.pk,
        action="update",
        changes=changes,
        performed_by=performed_by,
    )


@receiver(pre_save, sender=Asset)
def snapshot_asset(sender, instance: Asset, **kwargs):
    if not instance.pk:
        instance._pre_save_snapshot = None
        return
    previous = Asset.objects.filter(pk=instance.pk).values(
        "status",
        "condition",
        "current_location_id",
    ).first()
    instance._pre_save_snapshot = previous


@receiver(post_save, sender=Asset)
def audit_asset(sender, instance: Asset, created: bool, **kwargs):
    if created:
        return
    previous = getattr(instance, "_pre_save_snapshot", None) or {}
    changes = {}
    if previous.get("status") and previous.get("status") != instance.status:
        changes["status"] = {"before": previous.get("status"), "after": instance.status}
    if previous.get("condition") and previous.get("condition") != instance.condition:
        changes["condition"] = {
            "before": previous.get("condition"),
            "after": instance.condition,
        }
    if (
        previous.get("current_location_id")
        and previous.get("current_location_id") != instance.current_location_id
    ):
        changes["current_location"] = {
            "before": previous.get("current_location_id"),
            "after": instance.current_location_id,
        }
    _log_asset_change(instance, changes)


@receiver(m2m_changed, sender=Asset.responsible_users.through)
def audit_asset_responsible(sender, instance: Asset, action: str, pk_set, **kwargs):
    if action in {"pre_add", "pre_remove", "pre_clear"}:
        instance._responsible_before = list(
            instance.responsible_users.values_list("id", flat=True)
        )
        return
    if action not in {"post_add", "post_remove", "post_clear"}:
        return
    before_ids = getattr(instance, "_responsible_before", [])
    after_ids = list(instance.responsible_users.values_list("id", flat=True))
    changes = {
        "responsible_users": {
            "before": before_ids,
            "after": after_ids,
        }
    }
    _log_asset_change(instance, changes)
