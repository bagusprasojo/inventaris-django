from django.contrib import admin

from .models import (
    Asset,
    AssetCodeCounter,
    AssetDeletion,
    AssetLocationHistory,
    AssetMeterReading,
    AssetPhoto,
    AssetResponsibility,
    AuditLog,
    Category,
    Loan,
    Location,
    Maintenance,
    MaintenancePhoto,
    MaintenanceSchedule,
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_active", "created_at")
    search_fields = ("code", "name")
    list_filter = ("is_active",)


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ("name", "parent", "level", "is_active")
    search_fields = ("name", "path")
    list_filter = ("is_active", "level")


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "category", "status", "condition", "current_location")
    search_fields = ("code", "name")
    list_filter = ("status", "condition", "category")
    filter_horizontal = ("responsible_users",)


@admin.register(AssetResponsibility)
class AssetResponsibilityAdmin(admin.ModelAdmin):
    list_display = ("asset", "user", "assigned_at")
    search_fields = ("asset__code", "asset__name", "user__username")


@admin.register(AssetLocationHistory)
class AssetLocationHistoryAdmin(admin.ModelAdmin):
    list_display = ("asset", "from_location", "to_location", "moved_at", "moved_by")
    search_fields = ("asset__code", "asset__name")


@admin.register(AssetPhoto)
class AssetPhotoAdmin(admin.ModelAdmin):
    list_display = ("asset", "caption", "uploaded_by", "created_at")
    search_fields = ("asset__code", "asset__name", "caption")


@admin.register(AssetMeterReading)
class AssetMeterReadingAdmin(admin.ModelAdmin):
    list_display = ("asset", "reading_type", "reading_value", "reading_at", "recorded_by")
    list_filter = ("reading_type",)
    search_fields = ("asset__code", "asset__name", "note")


@admin.register(MaintenanceSchedule)
class MaintenanceScheduleAdmin(admin.ModelAdmin):
    list_display = (
        "asset",
        "plan_name",
        "trigger_type",
        "period",
        "next_due_date",
        "usage_interval",
        "usage_reading_type",
        "last_usage_value",
        "next_due_usage",
        "status",
    )
    list_filter = ("trigger_type", "period", "usage_reading_type", "status")
    search_fields = ("asset__code", "asset__name")


@admin.register(Maintenance)
class MaintenanceAdmin(admin.ModelAdmin):
    list_display = ("asset", "type", "performed_at", "created_by")
    list_filter = ("type",)
    search_fields = ("asset__code", "asset__name")


@admin.register(MaintenancePhoto)
class MaintenancePhotoAdmin(admin.ModelAdmin):
    list_display = ("maintenance", "caption", "uploaded_by", "created_at")
    search_fields = ("maintenance__asset__code", "maintenance__asset__name", "caption")


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ("asset", "borrower", "borrowed_at", "planned_return_at", "returned_at")
    list_filter = ("returned_at",)
    search_fields = ("asset__code", "asset__name", "borrower__username")


@admin.register(AssetDeletion)
class AssetDeletionAdmin(admin.ModelAdmin):
    list_display = ("asset", "deleted_by", "deleted_at")
    search_fields = ("asset__code", "asset__name")


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("entity", "entity_id", "action", "performed_by", "performed_at")
    search_fields = ("entity", "entity_id")


@admin.register(AssetCodeCounter)
class AssetCodeCounterAdmin(admin.ModelAdmin):
    list_display = ("year", "month", "counter")
