from django.core.management.base import BaseCommand

from inventaris.models import Category, Location


class Command(BaseCommand):
    help = "Seed initial categories and locations for inventaris"

    def handle(self, *args, **options):
        categories = [
            ("ELEK", "Elektronik"),
            ("MEB", "Meubel"),
            ("GDG", "Gedung"),
            ("KDR", "Kendaraan"),
            ("LAIN", "Lainnya"),
        ]

        for code, name in categories:
            Category.objects.get_or_create(code=code, defaults={"name": name})

        gedung_a, _ = Location.objects.get_or_create(name="Gedung A", parent=None)
        gedung_b, _ = Location.objects.get_or_create(name="Gedung B", parent=None)
        Location.objects.get_or_create(name="Ruang 101", parent=gedung_a)
        Location.objects.get_or_create(name="Ruang 102", parent=gedung_a)
        Location.objects.get_or_create(name="Ruang Lab", parent=gedung_b)

        self.stdout.write(self.style.SUCCESS("Seed inventaris selesai."))
