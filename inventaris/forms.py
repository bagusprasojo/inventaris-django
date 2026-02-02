from django import forms
from django.contrib.auth.forms import AuthenticationForm

from .models import (
    Asset,
    AssetDeletion,
    AssetLocationHistory,
    AssetMeterReading,
    AssetPhoto,
    Category,
    Loan,
    Location,
    Maintenance,
    MaintenancePhoto,
    MaintenanceSchedule,
)


class BootstrapFormMixin:
    """Apply Bootstrap 5 classes and invalid styles to form widgets."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            widget = field.widget
            existing = widget.attrs.get("class", "")

            if isinstance(widget, forms.CheckboxInput):
                css_class = "form-check-input"
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                css_class = "form-select"
            else:
                css_class = "form-control"

            widget.attrs["class"] = f"{existing} {css_class}".strip()

            if self.is_bound and self.errors.get(name):
                widget.attrs["class"] = f"{widget.attrs['class']} is-invalid".strip()


class BootstrapModelForm(BootstrapFormMixin, forms.ModelForm):
    pass


class BootstrapAuthenticationForm(BootstrapFormMixin, AuthenticationForm):
    pass


class CategoryForm(BootstrapModelForm):
    class Meta:
        model = Category
        fields = ["code", "name", "is_active"]


class LocationForm(BootstrapModelForm):
    class Meta:
        model = Location
        fields = ["name", "parent", "is_active"]


class AssetForm(BootstrapModelForm):
    class Meta:
        model = Asset
        fields = [
            "name",
            "category",
            "acquired_date",
            "status",
            "condition",
            "current_location",
            "responsible_users",
        ]
        widgets = {
            "acquired_date": forms.DateInput(attrs={"type": "date"}),
            "responsible_users": forms.SelectMultiple(attrs={"size": 6}),
        }


class AssetPhotoForm(BootstrapModelForm):
    class Meta:
        model = AssetPhoto
        fields = ["image", "caption"]


class AssetMeterReadingForm(BootstrapModelForm):
    class Meta:
        model = AssetMeterReading
        fields = ["reading_type", "reading_value", "reading_at", "note"]
        widgets = {
            "reading_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }


class MaintenanceScheduleForm(BootstrapModelForm):
    class Meta:
        model = MaintenanceSchedule
        fields = [
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
        ]
        widgets = {
            "next_due_date": forms.DateInput(attrs={"type": "date"}),
        }

    def clean(self):
        cleaned = super().clean()
        trigger_type = cleaned.get("trigger_type")
        period = cleaned.get("period")
        next_due_date = cleaned.get("next_due_date")

        if trigger_type == MaintenanceSchedule.TRIGGER_TIME:
            if not period:
                self.add_error("period", "Period wajib diisi untuk trigger time-based.")
            if not next_due_date:
                self.add_error("next_due_date", "Tanggal jatuh tempo wajib diisi untuk trigger time-based.")
        elif trigger_type == MaintenanceSchedule.TRIGGER_USAGE:
            usage_interval = cleaned.get("usage_interval")
            usage_reading_type = cleaned.get("usage_reading_type")
            next_due_usage = cleaned.get("next_due_usage")
            if not usage_interval:
                self.add_error("usage_interval", "Interval usage wajib diisi untuk trigger usage-based.")
            if not usage_reading_type:
                self.add_error("usage_reading_type", "Tipe reading wajib dipilih untuk trigger usage-based.")
            if not next_due_usage:
                self.add_error("next_due_usage", "Next due usage wajib diisi untuk trigger usage-based.")
        return cleaned


class MaintenanceForm(BootstrapModelForm):
    reading_value = forms.IntegerField(
        required=False,
        min_value=0,
        label="Meter Reading",
        help_text="Wajib diisi jika jadwal yang dipilih bertipe usage-based.",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["schedule"].queryset = (
            MaintenanceSchedule.objects.select_related("asset")
            .filter(asset__deleted_at__isnull=True)
            .order_by("asset__code", "plan_name", "trigger_type", "next_due_date", "id")
        )

    def clean(self):
        cleaned = super().clean()
        schedule = cleaned.get("schedule")
        reading_value = cleaned.get("reading_value")
        if schedule and schedule.trigger_type == MaintenanceSchedule.TRIGGER_USAGE:
            if schedule.usage_reading_type is None:
                self.add_error(
                    "schedule",
                    "Jadwal usage-based belum memiliki tipe meter. Lengkapi jadwal dulu.",
                )
            if reading_value in (None, ""):
                self.add_error(
                    "reading_value",
                    "Meter reading wajib diisi untuk jadwal usage-based.",
                )
        return cleaned

    class Meta:
        model = Maintenance
        fields = [
            "asset",
            "type",
            "schedule",
            "condition_before",
            "condition_after",
            "cost",
            "performed_at",
            "note",
        ]
        widgets = {
            "performed_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }


class LoanForm(BootstrapModelForm):
    class Meta:
        model = Loan
        fields = [
            "asset",
            "borrower",
            "borrowed_at",
            "planned_return_at",
            "returned_at",
            "note",
        ]
        widgets = {
            "borrowed_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "planned_return_at": forms.DateInput(attrs={"type": "date"}),
            "returned_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }


class AssetMoveForm(BootstrapModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["note"].required = True

    class Meta:
        model = AssetLocationHistory
        fields = ["to_location", "moved_at", "note"]
        widgets = {
            "moved_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }
        labels = {
            "to_location": "Lokasi Tujuan",
            "moved_at": "Tanggal Mutasi",
            "note": "Catatan",
        }


class AssetDeleteForm(BootstrapModelForm):
    class Meta:
        model = AssetDeletion
        fields = ["reason"]


class MaintenancePhotoForm(BootstrapModelForm):
    class Meta:
        model = MaintenancePhoto
        fields = ["image", "caption"]
