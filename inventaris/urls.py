from django.urls import path
from django.contrib.auth import views as auth_views

from . import views
from .forms import BootstrapAuthenticationForm

app_name = "inventaris"

urlpatterns = [
    path("", views.DashboardView.as_view(), name="dashboard"),
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="inventaris/login.html",
            authentication_form=BootstrapAuthenticationForm,
        ),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("kategori/", views.CategoryListView.as_view(), name="category_list"),
    path("kategori/tambah/", views.CategoryCreateView.as_view(), name="category_create"),
    path("kategori/<int:pk>/edit/", views.CategoryUpdateView.as_view(), name="category_update"),
    path("lokasi/", views.LocationListView.as_view(), name="location_list"),
    path("lokasi/tambah/", views.LocationCreateView.as_view(), name="location_create"),
    path("lokasi/<int:pk>/edit/", views.LocationUpdateView.as_view(), name="location_update"),
    path("aset/", views.AssetListView.as_view(), name="asset_list"),
    path("aset/tambah/", views.AssetCreateView.as_view(), name="asset_create"),
    path("aset/<int:pk>/", views.AssetDetailView.as_view(), name="asset_detail"),
    path("aset/<int:pk>/edit/", views.AssetUpdateView.as_view(), name="asset_update"),
    path("aset/<int:pk>/mutasi/", views.AssetMoveView.as_view(), name="asset_move"),
    path("aset/<int:pk>/riwayat-lokasi/", views.AssetLocationHistoryListView.as_view(), name="asset_location_history"),
    path("aset/<int:pk>/hapus/", views.AssetDeleteView.as_view(), name="asset_delete"),
    path("aset/<int:pk>/label/", views.asset_label, name="asset_label"),
    path("aset/<int:pk>/foto/tambah/", views.AssetPhotoCreateView.as_view(), name="asset_photo_create"),
    path(
        "aset/<int:pk>/meter/tambah/",
        views.AssetMeterReadingCreateView.as_view(),
        name="asset_meter_create",
    ),
    path("jadwal/", views.MaintenanceScheduleListView.as_view(), name="schedule_list"),
    path("jadwal/tambah/", views.MaintenanceScheduleCreateView.as_view(), name="schedule_create"),
    path("jadwal/<int:pk>/edit/", views.MaintenanceScheduleUpdateView.as_view(), name="schedule_update"),
    path("jadwal/<int:pk>/hapus/", views.MaintenanceScheduleDeleteView.as_view(), name="schedule_delete"),
    path("pemeliharaan/", views.MaintenanceListView.as_view(), name="maintenance_list"),
    path("pemeliharaan/tambah/", views.MaintenanceCreateView.as_view(), name="maintenance_create"),
    path("pemeliharaan/<int:pk>/", views.MaintenanceDetailView.as_view(), name="maintenance_detail"),
    path("pemeliharaan/<int:pk>/edit/", views.MaintenanceUpdateView.as_view(), name="maintenance_update"),
    path("pemeliharaan/<int:pk>/hapus/", views.MaintenanceDeleteView.as_view(), name="maintenance_delete"),
    path(
        "pemeliharaan/<int:pk>/foto/tambah/",
        views.MaintenancePhotoCreateView.as_view(),
        name="maintenance_photo_create",
    ),
    path("peminjaman/", views.LoanListView.as_view(), name="loan_list"),
    path("peminjaman/tambah/", views.LoanCreateView.as_view(), name="loan_create"),
    path("peminjaman/<int:pk>/edit/", views.LoanUpdateView.as_view(), name="loan_update"),
    path("laporan/aset/", views.AssetReportView.as_view(), name="asset_report"),
    path("laporan/aset/excel/", views.asset_report_excel, name="asset_report_excel"),
    path("laporan/aset/pdf/", views.asset_report_pdf, name="asset_report_pdf"),
    path("laporan/pemeliharaan/", views.MaintenanceReportView.as_view(), name="maintenance_report"),
    path(
        "laporan/pemeliharaan/excel/",
        views.maintenance_report_excel,
        name="maintenance_report_excel",
    ),
    path(
        "laporan/pemeliharaan/pdf/",
        views.maintenance_report_pdf,
        name="maintenance_report_pdf",
    ),
    path("audit/", views.AuditLogListView.as_view(), name="audit_log_list"),
    path("jadwal/options/", views.schedule_options, name="schedule_options"),
    path("aset/<int:pk>/label/download/", views.asset_qr_download, name="asset_qr_download"),
]
