from __future__ import annotations

from django.conf import settings
from django.db import models, transaction
from django.utils import timezone


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Category(TimeStampedModel):
    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=150)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


class Location(TimeStampedModel):
    name = models.CharField(max_length=150)
    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        related_name="children",
        null=True,
        blank=True,
    )
    path = models.CharField(max_length=255, blank=True)
    level = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["path", "name"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._original_parent_id = self.parent_id

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        parent = self.parent
        new_path = f"{parent.path}/{self.pk}" if parent else str(self.pk)
        new_level = (parent.level + 1) if parent else 0
        if self.path != new_path or self.level != new_level:
            Location.objects.filter(pk=self.pk).update(path=new_path, level=new_level)
            self.path = new_path
            self.level = new_level
        self._original_parent_id = self.parent_id

    def __str__(self) -> str:
        return self.name


class AssetCodeCounter(models.Model):
    year = models.PositiveSmallIntegerField()
    month = models.PositiveSmallIntegerField()
    counter = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["year", "month"], name="uniq_asset_code_ym"),
        ]

    @classmethod
    def next_code(cls, acquired_date: timezone.datetime.date) -> str:
        year = acquired_date.year
        month = acquired_date.month
        with transaction.atomic():
            counter_obj, _ = cls.objects.select_for_update().get_or_create(
                year=year,
                month=month,
                defaults={"counter": 0},
            )
            counter_obj.counter += 1
            counter_obj.save(update_fields=["counter"])
        return f"{year:04d}-{month:02d}-{counter_obj.counter:04d}"


class Asset(TimeStampedModel):
    STATUS_AKTIF = "AKTIF"
    STATUS_DIPINJAM = "DIPINJAM"
    STATUS_RUSAK = "RUSAK"
    STATUS_DIHAPUS = "DIHAPUS"

    CONDITION_BAIK = "BAIK"
    CONDITION_RUSAK_RINGAN = "RUSAK_RINGAN"
    CONDITION_RUSAK_BERAT = "RUSAK_BERAT"

    STATUS_CHOICES = [
        (STATUS_AKTIF, "Aktif"),
        (STATUS_DIPINJAM, "Dipinjam"),
        (STATUS_RUSAK, "Rusak"),
        (STATUS_DIHAPUS, "Dihapus"),
    ]

    CONDITION_CHOICES = [
        (CONDITION_BAIK, "Baik"),
        (CONDITION_RUSAK_RINGAN, "Rusak Ringan"),
        (CONDITION_RUSAK_BERAT, "Rusak Berat"),
    ]

    code = models.CharField(max_length=20, unique=True, blank=True)
    name = models.CharField(max_length=200)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="assets")
    acquired_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_AKTIF)
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, default=CONDITION_BAIK)
    current_location = models.ForeignKey(Location, on_delete=models.PROTECT, related_name="assets")
    responsible_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="AssetResponsibility",
        related_name="responsible_assets",
        blank=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_assets",
        null=True,
        blank=True,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="updated_assets",
        null=True,
        blank=True,
    )
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["category"]),
            models.Index(fields=["current_location"]),
        ]

    def save(self, *args, **kwargs):
        if not self.code:
            if not self.acquired_date:
                raise ValueError("acquired_date is required to generate asset code")
            self.code = AssetCodeCounter.next_code(self.acquired_date)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


class AssetResponsibility(TimeStampedModel):
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    assigned_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["asset", "user"], name="uniq_asset_user"),
        ]

    def __str__(self) -> str:
        return f"{self.asset.code} -> {self.user_id}"


class AssetLocationHistory(TimeStampedModel):
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE)
    from_location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        related_name="moved_from_histories",
        null=True,
        blank=True,
    )
    to_location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        related_name="moved_to_histories",
    )
    moved_at = models.DateTimeField(default=timezone.now)
    moved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    note = models.TextField(blank=True)


class AssetPhoto(TimeStampedModel):
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE)
    image = models.ImageField(upload_to="asset_photos/")
    caption = models.CharField(max_length=255, blank=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)


class AssetMeterReading(TimeStampedModel):
    TYPE_KM = "KM"
    TYPE_HOUR = "HOUR"
    TYPE_CYCLE = "CYCLE"

    TYPE_CHOICES = [
        (TYPE_KM, "Kilometer"),
        (TYPE_HOUR, "Jam Operasi"),
        (TYPE_CYCLE, "Cycle Count"),
    ]

    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name="meter_readings")
    reading_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    reading_value = models.PositiveIntegerField()
    reading_at = models.DateTimeField(default=timezone.now)
    note = models.TextField(blank=True)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    class Meta:
        ordering = ["-reading_at", "-id"]


class MaintenanceSchedule(TimeStampedModel):
    TRIGGER_TIME = "TIME"
    TRIGGER_USAGE = "USAGE"
    TRIGGER_CONDITION = "CONDITION"
    TRIGGER_EVENT = "EVENT"

    PERIOD_HARIAN = "HARIAN"
    PERIOD_MINGGUAN = "MINGGUAN"
    PERIOD_BULANAN = "BULANAN"
    PERIOD_TAHUNAN = "TAHUNAN"

    STATUS_TEPAT = "TEPAT_WAKTU"
    STATUS_TERLAMBAT = "TERLAMBAT"

    TRIGGER_CHOICES = [
        (TRIGGER_TIME, "Time-based"),
        (TRIGGER_USAGE, "Usage-based"),
        (TRIGGER_CONDITION, "Condition-based"),
        (TRIGGER_EVENT, "Event-based"),
    ]

    PERIOD_CHOICES = [
        (PERIOD_HARIAN, "Harian"),
        (PERIOD_MINGGUAN, "Mingguan"),
        (PERIOD_BULANAN, "Bulanan"),
        (PERIOD_TAHUNAN, "Tahunan"),
    ]

    STATUS_CHOICES = [
        (STATUS_TEPAT, "Tepat Waktu"),
        (STATUS_TERLAMBAT, "Terlambat"),
    ]

    asset = models.ForeignKey(Asset, on_delete=models.CASCADE)
    plan_name = models.CharField(max_length=150, default="Rencana Pemeliharaan")
    trigger_type = models.CharField(
        max_length=20,
        choices=TRIGGER_CHOICES,
        default=TRIGGER_TIME,
    )
    period = models.CharField(max_length=20, choices=PERIOD_CHOICES, null=True, blank=True)
    next_due_date = models.DateField(null=True, blank=True)
    usage_interval = models.PositiveIntegerField(null=True, blank=True)
    usage_reading_type = models.CharField(
        max_length=20,
        choices=AssetMeterReading.TYPE_CHOICES,
        null=True,
        blank=True,
    )
    last_usage_value = models.PositiveIntegerField(null=True, blank=True)
    next_due_usage = models.PositiveIntegerField(null=True, blank=True)
    last_done_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_TEPAT)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    def __str__(self) -> str:
        label = self.plan_name
        if self.trigger_type == self.TRIGGER_TIME:
            return (
                f"{label} | {self.asset.code} | Time | {self.period or '-'} | due {self.next_due_date or '-'}"
            )
        if self.trigger_type == self.TRIGGER_USAGE:
            return (
                f"{label} | {self.asset.code} | Usage({self.usage_reading_type or '-'}) | interval {self.usage_interval or '-'} | due {self.next_due_usage or '-'}"
            )
        return f"{label} | {self.asset.code} | {self.get_trigger_type_display()}"


class Maintenance(TimeStampedModel):
    TYPE_RUTIN = "RUTIN"
    TYPE_INSIDENTAL = "INSIDENTAL"

    TYPE_CHOICES = [
        (TYPE_RUTIN, "Rutin"),
        (TYPE_INSIDENTAL, "Insidental"),
    ]

    asset = models.ForeignKey(Asset, on_delete=models.CASCADE)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    schedule = models.ForeignKey(
        MaintenanceSchedule,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    condition_before = models.CharField(max_length=20, choices=Asset.CONDITION_CHOICES)
    condition_after = models.CharField(max_length=20, choices=Asset.CONDITION_CHOICES)
    cost = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    performed_at = models.DateTimeField()
    note = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)


class MaintenancePhoto(TimeStampedModel):
    maintenance = models.ForeignKey(Maintenance, on_delete=models.CASCADE, related_name="photos")
    image = models.ImageField(upload_to="maintenance_photos/")
    caption = models.CharField(max_length=255, blank=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)


class Loan(TimeStampedModel):
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE)
    borrower = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="asset_loans",
    )
    borrowed_at = models.DateTimeField(default=timezone.now)
    planned_return_at = models.DateField()
    returned_at = models.DateTimeField(null=True, blank=True)
    note = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_asset_loans",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["asset"],
                condition=models.Q(returned_at__isnull=True),
                name="uniq_active_loan_per_asset",
            ),
        ]


class AssetDeletion(TimeStampedModel):
    asset = models.OneToOneField(Asset, on_delete=models.CASCADE)
    reason = models.TextField()
    deleted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    deleted_at = models.DateTimeField(default=timezone.now)


class AuditLog(TimeStampedModel):
    entity = models.CharField(max_length=50)
    entity_id = models.PositiveIntegerField()
    action = models.CharField(max_length=50)
    changes = models.JSONField()
    performed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    performed_at = models.DateTimeField(default=timezone.now)
