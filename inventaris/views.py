from __future__ import annotations

from datetime import date, datetime

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
import base64
from io import BytesIO

from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, TemplateView, UpdateView
from django.utils import timezone

from .forms import (
    AssetForm,
    AssetDeleteForm,
    AssetMeterReadingForm,
    AssetMoveForm,
    AssetPhotoForm,
    CategoryForm,
    LoanForm,
    LocationForm,
    MaintenanceForm,
    MaintenancePhotoForm,
    MaintenanceScheduleForm,
)
from .models import (
    Asset,
    AssetLocationHistory,
    AssetDeletion,
    AssetMeterReading,
    AssetPhoto,
    AuditLog,
    Category,
    Loan,
    Location,
    Maintenance,
    MaintenancePhoto,
    MaintenanceSchedule,
)
from .utils import add_period, schedule_status
from .mixins import RoleRequiredMixin
from .rbac import ALL_ROLES, ROLE_ADMIN, ROLE_SARPRAS, require_roles


class PublicHomeView(TemplateView):
    template_name = "inventaris/public_home.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return HttpResponseRedirect(reverse_lazy("inventaris:dashboard"))
        return super().dispatch(request, *args, **kwargs)


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _asset_report_queryset(request):
    qs = Asset.objects.filter(deleted_at__isnull=True).select_related(
        "category", "current_location"
    )
    status = request.GET.get("status")
    category = request.GET.get("category")
    location = request.GET.get("location")
    if status:
        qs = qs.filter(status=status)
    if category:
        qs = qs.filter(category_id=category)
    if location:
        qs = qs.filter(current_location_id=location)
    return qs


def _maintenance_report_queryset(request):
    qs = Maintenance.objects.select_related("asset")
    date_from = _parse_date(request.GET.get("from"))
    date_to = _parse_date(request.GET.get("to"))
    mtype = request.GET.get("type")
    if date_from:
        qs = qs.filter(performed_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(performed_at__date__lte=date_to)
    if mtype:
        qs = qs.filter(type=mtype)
    return qs.order_by("-performed_at")


def _advance_schedule_after_maintenance(maintenance: Maintenance):
    schedule = maintenance.schedule
    if not schedule:
        return

    schedule.last_done_at = maintenance.performed_at

    if schedule.trigger_type == MaintenanceSchedule.TRIGGER_TIME:
        if schedule.next_due_date and schedule.period:
            base_date = (
                maintenance.performed_at.date()
                if maintenance.performed_at
                else schedule.next_due_date
            )
            schedule.next_due_date = add_period(base_date, schedule.period)
        schedule.status = schedule_status(schedule.next_due_date)
        schedule.save(update_fields=["last_done_at", "next_due_date", "status", "updated_at"])
        return

    if schedule.trigger_type == MaintenanceSchedule.TRIGGER_USAGE:
        latest_reading = (
            AssetMeterReading.objects.filter(
                asset=schedule.asset,
                reading_type=schedule.usage_reading_type,
            )
            .order_by("-reading_at", "-id")
            .first()
        )
        current_usage = (
            latest_reading.reading_value
            if latest_reading
            else (schedule.last_usage_value or schedule.next_due_usage)
        )
        schedule.last_usage_value = current_usage
        if schedule.usage_interval and current_usage is not None:
            schedule.next_due_usage = current_usage + schedule.usage_interval
        schedule.status = MaintenanceSchedule.STATUS_TEPAT
        schedule.save(
            update_fields=[
                "last_done_at",
                "last_usage_value",
                "next_due_usage",
                "status",
                "updated_at",
            ]
        )


class CategoryListView(RoleRequiredMixin, ListView):
    model = Category
    template_name = "inventaris/category_list.html"
    context_object_name = "categories"
    allowed_roles = ALL_ROLES


class CategoryCreateView(RoleRequiredMixin, CreateView):
    model = Category
    form_class = CategoryForm
    template_name = "inventaris/category_form.html"
    success_url = reverse_lazy("inventaris:category_list")
    allowed_roles = (ROLE_ADMIN, ROLE_SARPRAS)


class CategoryUpdateView(RoleRequiredMixin, UpdateView):
    model = Category
    form_class = CategoryForm
    template_name = "inventaris/category_form.html"
    success_url = reverse_lazy("inventaris:category_list")
    allowed_roles = (ROLE_ADMIN, ROLE_SARPRAS)


class LocationListView(RoleRequiredMixin, ListView):
    model = Location
    template_name = "inventaris/location_list.html"
    context_object_name = "locations"
    allowed_roles = ALL_ROLES


class LocationCreateView(RoleRequiredMixin, CreateView):
    model = Location
    form_class = LocationForm
    template_name = "inventaris/location_form.html"
    success_url = reverse_lazy("inventaris:location_list")
    allowed_roles = (ROLE_ADMIN, ROLE_SARPRAS)


class LocationUpdateView(RoleRequiredMixin, UpdateView):
    model = Location
    form_class = LocationForm
    template_name = "inventaris/location_form.html"
    success_url = reverse_lazy("inventaris:location_list")
    allowed_roles = (ROLE_ADMIN, ROLE_SARPRAS)


class AssetListView(RoleRequiredMixin, ListView):
    model = Asset
    template_name = "inventaris/asset_list.html"
    context_object_name = "assets"
    allowed_roles = ALL_ROLES

    def get_queryset(self):
        return Asset.objects.filter(deleted_at__isnull=True).select_related(
            "category", "current_location"
        )


class AssetDetailView(RoleRequiredMixin, DetailView):
    model = Asset
    template_name = "inventaris/asset_detail.html"
    context_object_name = "asset"
    allowed_roles = ALL_ROLES

    def get_template_names(self):
        if self.request.GET.get("scan") == "1":
            return ["inventaris/asset_detail_scan.html"]
        return [self.template_name]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["location_histories"] = (
            AssetLocationHistory.objects.filter(asset=self.object)
            .select_related("from_location", "to_location", "moved_by")
            .order_by("-moved_at")
        )
        context["asset_photos"] = (
            AssetPhoto.objects.filter(asset=self.object).order_by("-created_at")
        )
        context["meter_readings"] = (
            AssetMeterReading.objects.filter(asset=self.object)
            .select_related("recorded_by")
            .order_by("-reading_at")
        )
        context["loan_histories"] = (
            Loan.objects.filter(asset=self.object)
            .select_related("borrower")
            .order_by("-borrowed_at")
        )
        return context


class DashboardView(RoleRequiredMixin, ListView):
    model = MaintenanceSchedule
    template_name = "inventaris/dashboard.html"
    context_object_name = "schedules"
    allowed_roles = ALL_ROLES

    def get_queryset(self):
        return MaintenanceSchedule.objects.select_related("asset").order_by("next_due_date", "id")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = date.today()
        context["due_schedules"] = MaintenanceSchedule.objects.filter(
            trigger_type=MaintenanceSchedule.TRIGGER_TIME,
            next_due_date=today,
        ).select_related("asset")
        context["overdue_schedules"] = MaintenanceSchedule.objects.filter(
            trigger_type=MaintenanceSchedule.TRIGGER_TIME,
            next_due_date__lt=today,
        ).select_related("asset")
        usage_schedules = MaintenanceSchedule.objects.filter(
            trigger_type=MaintenanceSchedule.TRIGGER_USAGE,
            next_due_usage__isnull=False,
            usage_reading_type__isnull=False,
        ).select_related("asset")
        latest_readings = (
            AssetMeterReading.objects.filter(asset_id__in=usage_schedules.values("asset_id"))
            .order_by("asset_id", "-reading_at", "-id")
        )
        latest_by_asset_type = {}
        for reading in latest_readings:
            key = (reading.asset_id, reading.reading_type)
            if key not in latest_by_asset_type:
                latest_by_asset_type[key] = reading

        usage_due_schedules = []
        usage_warning_schedules = []
        usage_overdue_schedules = []
        for schedule in usage_schedules:
            latest = latest_by_asset_type.get((schedule.asset_id, schedule.usage_reading_type))
            current_usage = latest.reading_value if latest else schedule.last_usage_value
            if current_usage is None:
                continue
            item = {
                "schedule": schedule,
                "current_usage": current_usage,
                "next_due_usage": schedule.next_due_usage,
            }
            if current_usage > schedule.next_due_usage:
                usage_overdue_schedules.append(item)
            elif current_usage == schedule.next_due_usage:
                usage_due_schedules.append(item)
            elif (
                schedule.usage_interval
                and schedule.next_due_usage
                and current_usage >= (schedule.next_due_usage - max(1, int(schedule.usage_interval * 0.1)))
            ):
                # Warning when remaining usage is in the last 10% interval.
                usage_warning_schedules.append(item)
        context["usage_due_schedules"] = usage_due_schedules
        context["usage_warning_schedules"] = usage_warning_schedules
        context["usage_overdue_schedules"] = usage_overdue_schedules
        context["today"] = today
        return context


class AssetCreateView(RoleRequiredMixin, CreateView):
    model = Asset
    form_class = AssetForm
    template_name = "inventaris/asset_form.html"
    success_url = reverse_lazy("inventaris:asset_list")
    allowed_roles = (ROLE_ADMIN, ROLE_SARPRAS)

    def form_valid(self, form):
        asset = form.save(commit=False)
        asset.created_by = self.request.user
        asset.updated_by = self.request.user
        asset.save()
        form.save_m2m()
        AssetLocationHistory.objects.create(
            asset=asset,
            from_location=None,
            to_location=asset.current_location,
            moved_by=self.request.user,
        )
        self.object = asset
        return HttpResponseRedirect(self.get_success_url())


class AssetUpdateView(RoleRequiredMixin, UpdateView):
    model = Asset
    form_class = AssetForm
    template_name = "inventaris/asset_form.html"
    success_url = reverse_lazy("inventaris:asset_list")
    allowed_roles = (ROLE_ADMIN, ROLE_SARPRAS)

    def form_valid(self, form):
        previous_location = self.object.current_location
        asset = form.save(commit=False)
        asset.updated_by = self.request.user
        asset.save()
        form.save_m2m()
        if previous_location != asset.current_location:
            AssetLocationHistory.objects.create(
                asset=asset,
                from_location=previous_location,
                to_location=asset.current_location,
                moved_by=self.request.user,
            )
        self.object = asset
        return HttpResponseRedirect(self.get_success_url())


class AssetPhotoCreateView(RoleRequiredMixin, CreateView):
    model = AssetPhoto
    form_class = AssetPhotoForm
    template_name = "inventaris/asset_photo_form.html"
    allowed_roles = (ROLE_ADMIN, ROLE_SARPRAS)

    def get_success_url(self):
        return reverse_lazy("inventaris:asset_detail", kwargs={"pk": self.kwargs["pk"]})

    def form_valid(self, form):
        asset = Asset.objects.get(pk=self.kwargs["pk"])
        photo = form.save(commit=False)
        photo.asset = asset
        photo.uploaded_by = self.request.user
        photo.save()
        self.object = photo
        return HttpResponseRedirect(self.get_success_url())


class AssetMeterReadingCreateView(RoleRequiredMixin, CreateView):
    model = AssetMeterReading
    form_class = AssetMeterReadingForm
    template_name = "inventaris/asset_meter_form.html"
    allowed_roles = (ROLE_ADMIN, ROLE_SARPRAS)

    def get_success_url(self):
        return reverse_lazy("inventaris:asset_detail", kwargs={"pk": self.kwargs["pk"]})

    def form_valid(self, form):
        asset = Asset.objects.get(pk=self.kwargs["pk"])
        reading = form.save(commit=False)
        reading.asset = asset
        reading.recorded_by = self.request.user
        reading.save()
        self.object = reading
        return HttpResponseRedirect(self.get_success_url())


class AssetMoveView(RoleRequiredMixin, UpdateView):
    model = Asset
    form_class = AssetMoveForm
    template_name = "inventaris/asset_move_form.html"
    allowed_roles = (ROLE_ADMIN, ROLE_SARPRAS)

    def get_success_url(self):
        return reverse_lazy("inventaris:asset_detail", kwargs={"pk": self.object.pk})

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        current_location_id = self.object.current_location_id
        form.fields["to_location"].queryset = (
            Location.objects.filter(is_active=True).exclude(pk=current_location_id)
        )
        form.fields["moved_at"].initial = timezone.now()
        return form

    def form_valid(self, form):
        asset = self.object
        previous_location = asset.current_location
        new_location = form.cleaned_data["to_location"]
        note = form.cleaned_data.get("note", "")
        moved_at = form.cleaned_data.get("moved_at") or timezone.now()
        if previous_location != new_location:
            asset.current_location = new_location
            asset.updated_by = self.request.user
            asset.save(update_fields=["current_location", "updated_by", "updated_at"])
            AssetLocationHistory.objects.create(
                asset=asset,
                from_location=previous_location,
                to_location=new_location,
                moved_by=self.request.user,
                note=note,
                moved_at=moved_at,
            )
        return HttpResponseRedirect(self.get_success_url())


class AssetLocationHistoryListView(RoleRequiredMixin, ListView):
    model = AssetLocationHistory
    template_name = "inventaris/asset_location_history.html"
    context_object_name = "histories"
    allowed_roles = ALL_ROLES

    def get_queryset(self):
        return (
            AssetLocationHistory.objects.filter(asset_id=self.kwargs["pk"])
            .select_related("from_location", "to_location", "moved_by", "asset")
            .order_by("-moved_at")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["asset"] = Asset.objects.get(pk=self.kwargs["pk"])
        return context


class AssetDeleteView(RoleRequiredMixin, UpdateView):
    model = Asset
    form_class = AssetDeleteForm
    template_name = "inventaris/asset_delete_form.html"
    success_url = reverse_lazy("inventaris:asset_list")
    allowed_roles = (ROLE_ADMIN, ROLE_SARPRAS)

    def form_valid(self, form):
        asset = self.object
        if asset.deleted_at:
            return HttpResponseRedirect(self.get_success_url())
        AssetDeletion.objects.create(
            asset=asset,
            reason=form.cleaned_data["reason"],
            deleted_by=self.request.user,
        )
        asset.status = Asset.STATUS_DIHAPUS
        asset.deleted_at = timezone.now()
        asset.updated_by = self.request.user
        asset.save(update_fields=["status", "deleted_at", "updated_by", "updated_at"])
        self.object = asset
        return HttpResponseRedirect(self.get_success_url())


class MaintenanceScheduleListView(RoleRequiredMixin, ListView):
    model = MaintenanceSchedule
    template_name = "inventaris/schedule_list.html"
    context_object_name = "schedules"
    allowed_roles = ALL_ROLES


class MaintenanceScheduleCreateView(RoleRequiredMixin, CreateView):
    model = MaintenanceSchedule
    form_class = MaintenanceScheduleForm
    template_name = "inventaris/schedule_form.html"
    success_url = reverse_lazy("inventaris:schedule_list")
    allowed_roles = (ROLE_ADMIN, ROLE_SARPRAS)

    def form_valid(self, form):
        schedule = form.save(commit=False)
        schedule.created_by = self.request.user
        if schedule.trigger_type != MaintenanceSchedule.TRIGGER_TIME:
            schedule.period = None
            schedule.next_due_date = None
        if schedule.trigger_type != MaintenanceSchedule.TRIGGER_USAGE:
            schedule.usage_interval = None
            schedule.usage_reading_type = None
            schedule.last_usage_value = None
            schedule.next_due_usage = None
        schedule.status = schedule_status(schedule.next_due_date)
        schedule.save()
        self.object = schedule
        return HttpResponseRedirect(self.get_success_url())


class MaintenanceScheduleUpdateView(RoleRequiredMixin, UpdateView):
    model = MaintenanceSchedule
    form_class = MaintenanceScheduleForm
    template_name = "inventaris/schedule_form.html"
    success_url = reverse_lazy("inventaris:schedule_list")
    allowed_roles = (ROLE_ADMIN, ROLE_SARPRAS)

    def form_valid(self, form):
        schedule = form.save(commit=False)
        if schedule.trigger_type != MaintenanceSchedule.TRIGGER_TIME:
            schedule.period = None
            schedule.next_due_date = None
        if schedule.trigger_type != MaintenanceSchedule.TRIGGER_USAGE:
            schedule.usage_interval = None
            schedule.usage_reading_type = None
            schedule.last_usage_value = None
            schedule.next_due_usage = None
        schedule.status = schedule_status(schedule.next_due_date)
        schedule.save()
        self.object = schedule
        return HttpResponseRedirect(self.get_success_url())


class MaintenanceScheduleDeleteView(RoleRequiredMixin, DeleteView):
    model = MaintenanceSchedule
    template_name = "inventaris/schedule_delete_form.html"
    success_url = reverse_lazy("inventaris:schedule_list")
    allowed_roles = (ROLE_ADMIN, ROLE_SARPRAS)


class MaintenanceListView(RoleRequiredMixin, ListView):
    model = Maintenance
    template_name = "inventaris/maintenance_list.html"
    context_object_name = "maintenances"
    allowed_roles = ALL_ROLES

    def get_queryset(self):
        return Maintenance.objects.select_related("asset").order_by("-performed_at")


class MaintenanceCreateView(RoleRequiredMixin, CreateView):
    model = Maintenance
    form_class = MaintenanceForm
    template_name = "inventaris/maintenance_form.html"
    success_url = reverse_lazy("inventaris:maintenance_list")
    allowed_roles = (ROLE_ADMIN, ROLE_SARPRAS)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["usage_type_map"] = {
            choice[0]: choice[1] for choice in AssetMeterReading.TYPE_CHOICES
        }
        return context

    def form_valid(self, form):
        maintenance = form.save(commit=False)
        maintenance.created_by = self.request.user
        maintenance.save()
        asset = maintenance.asset
        asset.condition = maintenance.condition_after
        asset.updated_by = self.request.user
        asset.save(update_fields=["condition", "updated_by", "updated_at"])
        if maintenance.schedule and maintenance.schedule.trigger_type == MaintenanceSchedule.TRIGGER_USAGE:
            reading_value = form.cleaned_data.get("reading_value")
            if reading_value is not None:
                AssetMeterReading.objects.create(
                    asset=maintenance.asset,
                    reading_type=maintenance.schedule.usage_reading_type,
                    reading_value=reading_value,
                    reading_at=maintenance.performed_at,
                    note=maintenance.note or "",
                    recorded_by=self.request.user,
                )
        _advance_schedule_after_maintenance(maintenance)
        self.object = maintenance
        return HttpResponseRedirect(self.get_success_url())


class MaintenanceUpdateView(RoleRequiredMixin, UpdateView):
    model = Maintenance
    form_class = MaintenanceForm
    template_name = "inventaris/maintenance_form.html"
    success_url = reverse_lazy("inventaris:maintenance_list")
    allowed_roles = (ROLE_ADMIN, ROLE_SARPRAS)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["usage_type_map"] = {
            choice[0]: choice[1] for choice in AssetMeterReading.TYPE_CHOICES
        }
        return context

    def form_valid(self, form):
        maintenance = form.save(commit=False)
        maintenance.save()
        self.object = maintenance
        return HttpResponseRedirect(self.get_success_url())


class MaintenanceDeleteView(RoleRequiredMixin, DeleteView):
    model = Maintenance
    template_name = "inventaris/maintenance_delete_form.html"
    success_url = reverse_lazy("inventaris:maintenance_list")
    allowed_roles = (ROLE_ADMIN, ROLE_SARPRAS)


class MaintenancePhotoCreateView(RoleRequiredMixin, CreateView):
    model = MaintenancePhoto
    form_class = MaintenancePhotoForm
    template_name = "inventaris/maintenance_photo_form.html"
    allowed_roles = (ROLE_ADMIN, ROLE_SARPRAS)

    def get_success_url(self):
        return reverse_lazy("inventaris:maintenance_detail", kwargs={"pk": self.kwargs["pk"]})

    def form_valid(self, form):
        maintenance = Maintenance.objects.get(pk=self.kwargs["pk"])
        photo = form.save(commit=False)
        photo.maintenance = maintenance
        photo.uploaded_by = self.request.user
        photo.save()
        self.object = photo
        return HttpResponseRedirect(self.get_success_url())


class MaintenanceDetailView(RoleRequiredMixin, DetailView):
    model = Maintenance
    template_name = "inventaris/maintenance_detail.html"
    context_object_name = "maintenance"
    allowed_roles = ALL_ROLES

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["photos"] = self.object.photos.all().order_by("-created_at")
        return context


class LoanListView(RoleRequiredMixin, ListView):
    model = Loan
    template_name = "inventaris/loan_list.html"
    context_object_name = "loans"
    allowed_roles = ALL_ROLES

    def get_queryset(self):
        return Loan.objects.select_related("asset", "borrower").order_by("-borrowed_at")


class LoanCreateView(RoleRequiredMixin, CreateView):
    model = Loan
    form_class = LoanForm
    template_name = "inventaris/loan_form.html"
    success_url = reverse_lazy("inventaris:loan_list")
    allowed_roles = (ROLE_ADMIN, ROLE_SARPRAS)

    def form_valid(self, form):
        loan = form.save(commit=False)
        loan.created_by = self.request.user
        loan.save()
        asset = loan.asset
        asset.status = Asset.STATUS_DIPINJAM if loan.returned_at is None else Asset.STATUS_AKTIF
        asset.updated_by = self.request.user
        asset.save(update_fields=["status", "updated_by", "updated_at"])
        self.object = loan
        return HttpResponseRedirect(self.get_success_url())


class LoanUpdateView(RoleRequiredMixin, UpdateView):
    model = Loan
    form_class = LoanForm
    template_name = "inventaris/loan_form.html"
    success_url = reverse_lazy("inventaris:loan_list")
    allowed_roles = (ROLE_ADMIN, ROLE_SARPRAS)

    def form_valid(self, form):
        loan = form.save(commit=False)
        loan.save()
        asset = loan.asset
        if loan.returned_at:
            asset.status = Asset.STATUS_AKTIF
        asset.updated_by = self.request.user
        asset.save(update_fields=["status", "updated_by", "updated_at"])
        self.object = loan
        return HttpResponseRedirect(self.get_success_url())


class AssetReportView(RoleRequiredMixin, ListView):
    model = Asset
    template_name = "inventaris/asset_report.html"
    context_object_name = "assets"
    allowed_roles = ALL_ROLES

    def get_queryset(self):
        return _asset_report_queryset(self.request)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categories"] = Category.objects.all()
        context["locations"] = Location.objects.all()
        return context


class AuditLogListView(RoleRequiredMixin, ListView):
    model = AuditLog
    template_name = "inventaris/audit_log_list.html"
    context_object_name = "logs"
    paginate_by = 50
    allowed_roles = ALL_ROLES

    def get_queryset(self):
        qs = AuditLog.objects.select_related("performed_by").order_by("-performed_at")
        entity = self.request.GET.get("entity")
        action = self.request.GET.get("action")
        user_id = self.request.GET.get("user")
        if entity:
            qs = qs.filter(entity=entity)
        if action:
            qs = qs.filter(action=action)
        if user_id:
            qs = qs.filter(performed_by_id=user_id)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["entities"] = (
            AuditLog.objects.order_by()
            .values_list("entity", flat=True)
            .distinct()
        )
        context["actions"] = (
            AuditLog.objects.order_by()
            .values_list("action", flat=True)
            .distinct()
        )
        return context


@login_required
def schedule_options(request):
    require_roles(request.user, (ROLE_ADMIN, ROLE_SARPRAS))
    asset_id = request.GET.get("asset_id")
    if not asset_id:
        return JsonResponse({"options": []})
    schedules = (
        MaintenanceSchedule.objects.filter(asset_id=asset_id)
        .order_by("plan_name", "trigger_type", "next_due_date", "id")
    )
    options = []
    for schedule in schedules:
        options.append(
            {
                "id": schedule.id,
                "label": str(schedule),
                "usage_type": schedule.usage_reading_type,
                "usage_type_label": schedule.get_usage_reading_type_display()
                if schedule.usage_reading_type
                else "",
            }
        )
    return JsonResponse({"options": options})


@login_required
def asset_report_excel(request):
    require_roles(request.user, ALL_ROLES)
    queryset = _asset_report_queryset(request)
    try:
        from openpyxl import Workbook
    except ImportError:
        return HttpResponse("openpyxl belum terpasang.")
    wb = Workbook()
    ws = wb.active
    ws.title = "Aset"
    ws.append(["Kode", "Nama", "Kategori", "Lokasi", "Status", "Kondisi"])
    for item in queryset:
        ws.append(
            [
                item.code,
                item.name,
                str(item.category),
                str(item.current_location),
                item.get_status_display(),
                item.get_condition_display(),
            ]
        )
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = "attachment; filename=laporan_aset.xlsx"
    wb.save(response)
    return response


@login_required
def asset_report_pdf(request):
    require_roles(request.user, ALL_ROLES)
    queryset = _asset_report_queryset(request)
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
    except ImportError:
        return HttpResponse("reportlab belum terpasang.")
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = "attachment; filename=laporan_aset.pdf"
    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4
    y = height - 40
    p.setFont("Helvetica-Bold", 12)
    p.drawString(40, y, "Laporan Aset")
    y -= 20
    p.setFont("Helvetica", 10)
    for item in queryset:
        line = f"{item.code} | {item.name} | {item.category} | {item.current_location} | {item.get_status_display()} | {item.get_condition_display()}"
        p.drawString(40, y, line[:120])
        y -= 14
        if y < 60:
            p.showPage()
            y = height - 40
    p.save()
    return response


class MaintenanceReportView(RoleRequiredMixin, ListView):
    model = Maintenance
    template_name = "inventaris/maintenance_report.html"
    context_object_name = "maintenances"
    allowed_roles = ALL_ROLES

    def get_queryset(self):
        return _maintenance_report_queryset(self.request)


@login_required
def maintenance_report_excel(request):
    require_roles(request.user, ALL_ROLES)
    queryset = _maintenance_report_queryset(request)
    try:
        from openpyxl import Workbook
    except ImportError:
        return HttpResponse("openpyxl belum terpasang.")
    wb = Workbook()
    ws = wb.active
    ws.title = "Pemeliharaan"
    ws.append(["Aset", "Tipe", "Tanggal", "Kondisi Sebelum", "Kondisi Sesudah", "Biaya"])
    for item in queryset:
        ws.append(
            [
                str(item.asset),
                item.get_type_display(),
                item.performed_at.strftime("%Y-%m-%d %H:%M"),
                item.get_condition_before_display(),
                item.get_condition_after_display(),
                float(item.cost),
            ]
        )
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = "attachment; filename=laporan_pemeliharaan.xlsx"
    wb.save(response)
    return response


@login_required
def maintenance_report_pdf(request):
    require_roles(request.user, ALL_ROLES)
    queryset = _maintenance_report_queryset(request)
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
    except ImportError:
        return HttpResponse("reportlab belum terpasang.")
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = "attachment; filename=laporan_pemeliharaan.pdf"
    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4
    y = height - 40
    p.setFont("Helvetica-Bold", 12)
    p.drawString(40, y, "Laporan Pemeliharaan")
    y -= 20
    p.setFont("Helvetica", 10)
    for item in queryset:
        line = (
            f"{item.asset} | {item.get_type_display()} | {item.performed_at.strftime('%Y-%m-%d')} "
            f"| {item.get_condition_before_display()} -> {item.get_condition_after_display()} | {float(item.cost)}"
        )
        p.drawString(40, y, line[:120])
        y -= 14
        if y < 60:
            p.showPage()
            y = height - 40
    p.save()
    return response


@login_required
def asset_label(request, pk: int):
    require_roles(request.user, (ROLE_ADMIN, ROLE_SARPRAS))
    asset = Asset.objects.select_related("category", "current_location").get(pk=pk)
    detail_url = request.build_absolute_uri(
        reverse_lazy("inventaris:asset_detail", kwargs={"pk": asset.pk})
    )
    scan_url = f"{detail_url}?scan=1"
    qr_text = f"{asset.code} | {asset.name} | {scan_url}"
    try:
        import qrcode
    except ImportError:
        return HttpResponse("qrcode belum terpasang.")
    qr = qrcode.QRCode(border=2, box_size=4)
    qr.add_data(qr_text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    qr_b64 = base64.b64encode(buffer.getvalue()).decode("ascii")
    return render(
        request,
        "inventaris/asset_label.html",
        {
            "asset": asset,
            "qr_b64": qr_b64,
            "detail_url": scan_url,
        },
    )


@login_required
def asset_qr_download(request, pk: int):
    require_roles(request.user, (ROLE_ADMIN, ROLE_SARPRAS))
    asset = Asset.objects.select_related("category", "current_location").get(pk=pk)
    detail_url = request.build_absolute_uri(
        reverse_lazy("inventaris:asset_detail", kwargs={"pk": asset.pk})
    )
    scan_url = f"{detail_url}?scan=1"
    qr_text = f"{asset.code} | {asset.name} | {scan_url}"
    try:
        import qrcode
    except ImportError:
        return HttpResponse("qrcode belum terpasang.")
    qr = qrcode.QRCode(border=2, box_size=4)
    qr.add_data(qr_text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    response = HttpResponse(buffer.getvalue(), content_type="image/png")
    response["Content-Disposition"] = f"attachment; filename={asset.code}_qrcode.png"
    return response
