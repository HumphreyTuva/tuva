from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand

from shop.models import Product


SAMPLE_IMAGES = Path(__file__).resolve().parents[4] / "frontend" / "public" / "products"

# Prices are the supplied KSh prices plus KSh 3,000.
ROWS = [
    ("HP ProBook 11 G7 EE Chromebook", "4GB RAM · 32GB storage", "business", 10_500, ["Chromebook", "4GB RAM", "32GB storage"], "probook.png"),
    ("HP ProBook 650 G4", "Core i5 7th Gen · 8GB RAM · 256GB SSD", "business", 25_500, ["Core i5 7th Gen", "8GB RAM", "256GB SSD"], "probook.png"),
    ("HP ProBook 650 G5", "Core i7 · 16GB RAM · 500GB storage", "business", 30_500, ["Core i7", "16GB RAM", "500GB storage"], "probook.png"),
    ("HP ProBook 430 G5", "Core i7 8th Gen · 8GB RAM · 500GB storage", "business", 29_500, ["Core i7 8th Gen", "8GB RAM", "500GB storage"], "probook.png"),
    ("HP ProBook 635 G8", "Ryzen 5 · 16GB RAM · 256GB SSD", "business", 31_000, ["Ryzen 5", "16GB RAM", "256GB SSD"], "probook.png"),
    ("HP Elite x2 G4", "Core i5 8th Gen · detachable · 8GB RAM · 256GB SSD", "2-in-1", 31_500, ["Core i5 8th Gen", "Detachable 2-in-1", "8GB RAM", "256GB SSD"], "flex.png"),
    ("HP EliteBook 830 G7", "Core i5 10th Gen · 16GB RAM · 256GB SSD", "business", 33_000, ["Core i5 10th Gen", "16GB RAM", "256GB SSD"], "probook.png"),
    ("HP EliteBook 840 G8", "Core i5 11th Gen · 8GB RAM · 256GB SSD", "business", 34_000, ["Core i5 11th Gen", "8GB RAM", "256GB SSD"], "probook.png"),
    ("HP EliteBook 850 G6", "Core i5 8th Gen · 16GB RAM · 512GB SSD", "business", 35_000, ["Core i5 8th Gen", "16GB RAM", "512GB SSD"], "probook.png"),
    ("HP 15", "Core i7 8th Gen · 16GB RAM · 256GB SSD · 2GB NVIDIA graphics", "business", 41_000, ["Core i7 8th Gen", "16GB RAM", "256GB SSD", "2GB NVIDIA graphics"], "probook.png"),
    ("HP ZBook Firefly 14 G7", "Core i7 10th Gen · touch · 16GB RAM · 256GB SSD", "business", 43_000, ["Core i7 10th Gen", "Touchscreen", "16GB RAM", "256GB SSD"], "probook.png"),
    ("HP EliteBook 1040 G6 x360", "Core i7 8th Gen · touchscreen · 16GB RAM · 256GB SSD", "2-in-1", 45_000, ["Core i7 8th Gen", "x360 touchscreen", "16GB RAM", "256GB SSD"], "flex.png"),
    ("HP Dragonfly G2 x360", "Core i5 11th Gen · touchscreen · 16GB RAM · 256GB SSD", "2-in-1", 48_000, ["Core i5 11th Gen", "x360 touchscreen", "16GB RAM", "256GB SSD"], "flex.png"),
    ("HP EliteBook 850 G8", "Core i7 11th Gen · 16GB RAM · 256GB SSD", "business", 48_000, ["Core i7 11th Gen", "16GB RAM", "256GB SSD"], "probook.png"),
    ("HP EliteBook 1040 G8 x360", "Core i7 11th Gen · touchscreen · 16GB RAM · 512GB SSD", "2-in-1", 61_000, ["Core i7 11th Gen", "x360 touchscreen", "16GB RAM", "512GB SSD"], "flex.png"),
    ("HP Pavilion Plus 14", "Core i5 13th Gen · 16GB RAM · 512GB SSD · boxed", "business", 68_000, ["Core i5 13th Gen", "16GB RAM", "512GB SSD", "Boxed"], "ultrabook.png"),
    ("HP EliteBook 1040 G10 x360", "Core i7 13th Gen · touchscreen · 16GB RAM · 256GB SSD", "2-in-1", 73_000, ["Core i7 13th Gen", "x360 touchscreen", "16GB RAM", "256GB SSD"], "flex.png"),
    ("HP OMEN 16", "Core i7 11th Gen · 32GB RAM · 512GB SSD · RTX 3070 8GB", "gaming", 103_000, ["Core i7 11th Gen", "32GB RAM", "512GB SSD", "NVIDIA RTX 3070 8GB"], "gamepro.png"),
]


ADDITIONAL_ROWS = [
    ("HP Chromebook 4GB 16GB", "4GB RAM | 16GB storage", "business", 10_500, ["4GB RAM", "16GB storage"], "probook.png"),
    ("Epson Core i3 6th Gen 4GB 500GB", "Core i3 6th Gen | 4GB RAM | 500GB storage", "business", 11_500, ["Core i3 6th Gen", "4GB RAM", "500GB storage"], "probook.png"),
    ("Epson Core i3 6th Gen 8GB 256GB SSD", "Core i3 6th Gen | 8GB RAM | 256GB SSD", "business", 13_000, ["Core i3 6th Gen", "8GB RAM", "256GB SSD"], "probook.png"),
    ("Sony Core i3 6th Gen 4GB 256GB SSD", "Core i3 6th Gen | 4GB RAM | 256GB SSD", "business", 12_500, ["Core i3 6th Gen", "4GB RAM", "256GB SSD"], "probook.png"),
    ("Sony Core i3 6th Gen 8GB 500GB", "Core i3 6th Gen | 8GB RAM | 500GB storage", "business", 13_000, ["Core i3 6th Gen", "8GB RAM", "500GB storage"], "probook.png"),
    ("NEC Core i5 6th Gen 4GB 256GB SSD", "Core i5 6th Gen | 4GB RAM | 256GB SSD", "business", 13_000, ["Core i5 6th Gen", "4GB RAM", "256GB SSD"], "probook.png"),
    ("NEC Core i5 6th Gen 4GB 128GB SSD", "Core i5 6th Gen | 4GB RAM | 128GB SSD", "business", 12_000, ["Core i5 6th Gen", "4GB RAM", "128GB SSD"], "probook.png"),
    ("NEC Core i5 6th Gen 8GB 256GB SSD", "Core i5 6th Gen | 8GB RAM | 256GB SSD", "business", 15_000, ["Core i5 6th Gen", "8GB RAM", "256GB SSD"], "probook.png"),
    ("Panasonic Core i5 7th Gen 4GB 128GB SSD Touch", "Touchscreen | Core i5 7th Gen | 4GB RAM | 128GB SSD", "2-in-1", 15_500, ["Core i5 7th Gen", "4GB RAM", "128GB SSD", "Touchscreen"], "flex.png"),
    ("Panasonic Core i5 7th Gen 8GB 256GB SSD", "Core i5 7th Gen | 8GB RAM | 256GB SSD", "business", 16_500, ["Core i5 7th Gen", "8GB RAM", "256GB SSD"], "probook.png"),
    ("Lenovo 300 Celeron x360", "Celeron | 4GB RAM | 128GB SSD | touchscreen | stylus", "2-in-1", 18_000, ["Celeron", "4GB RAM", "128GB SSD", "x360 touchscreen", "Stylus"], "flex.png"),
    ("HP Core i3 6th Gen Touch 4GB 128GB SSD", "Core i3 6th Gen | 4GB RAM | 128GB SSD | touchscreen", "2-in-1", 18_000, ["Core i3 6th Gen", "4GB RAM", "128GB SSD", "Touchscreen"], "flex.png"),
    ("Toshiba Core i5 4GB 500GB", "Core i5 | 4GB RAM | 500GB storage", "business", 13_000, ["Core i5", "4GB RAM", "500GB storage"], "probook.png"),
    ("HP EliteBook 820 G3 8GB 128GB SSD", "Core i5 | 8GB RAM | 128GB SSD", "business", 22_000, ["Core i5", "8GB RAM", "128GB SSD"], "probook.png"),
    ("HP EliteBook 820 G3 8GB 256GB SSD", "Core i5 | 8GB RAM | 256GB SSD", "business", 23_000, ["Core i5", "8GB RAM", "256GB SSD"], "probook.png"),
    ("HP EliteBook 840 G3 Core i5 8GB 256GB SSD", "Core i5 | 8GB RAM | 256GB SSD", "business", 23_000, ["Core i5", "8GB RAM", "256GB SSD"], "probook.png"),
    ("HP EliteBook 840 G3 Core i7 8GB 256GB SSD", "Core i7 6th Gen | 8GB RAM | 256GB SSD", "business", 25_500, ["Core i7 6th Gen", "8GB RAM", "256GB SSD"], "probook.png"),
    ("HP EliteBook 840 G3 Core i7 Touch 8GB 256GB SSD", "Core i7 6th Gen | 8GB RAM | 256GB SSD | touchscreen", "business", 27_000, ["Core i7 6th Gen", "8GB RAM", "256GB SSD", "Touchscreen"], "probook.png"),
    ("Lenovo ThinkPad T460s Core i5 4GB 256GB SSD", "Core i5 6th Gen | 4GB RAM | 256GB SSD", "business", 19_000, ["Core i5 6th Gen", "4GB RAM", "256GB SSD"], "probook.png"),
    ("Lenovo ThinkPad T460s Core i5 8GB 256GB SSD", "Core i5 6th Gen | 8GB RAM | 256GB SSD", "business", 21_500, ["Core i5 6th Gen", "8GB RAM", "256GB SSD"], "probook.png"),
    ("Lenovo ThinkPad T470s Core i5 Touch", "Core i5 6th Gen | 8GB RAM | 256GB SSD | touchscreen", "business", 23_000, ["Core i5 6th Gen", "8GB RAM", "256GB SSD", "Touchscreen"], "probook.png"),
    ("Lenovo ThinkPad Yoga X260 x360", "Core i5 6th Gen | 8GB RAM | 256GB SSD | touchscreen", "2-in-1", 25_000, ["Core i5 6th Gen", "8GB RAM", "256GB SSD", "x360 touchscreen"], "flex.png"),
    ("Lenovo ThinkPad P40 Yoga", "Core i7 6th Gen | 16GB RAM | 256GB SSD | 2GB graphics | touch x360", "2-in-1", 29_500, ["Core i7 6th Gen", "16GB RAM", "256GB SSD", "2GB graphics", "Touch x360"], "flex.png"),
    ("Lenovo ThinkPad Core i7 6th Gen 32GB 512GB SSD", "Core i7 6th Gen | 32GB RAM | 512GB SSD | 4GB graphics", "business", 41_500, ["Core i7 6th Gen", "32GB RAM", "512GB SSD", "4GB graphics"], "probook.png"),
    ("Panasonic Detachable Core i5 7th Gen 4GB 256GB SSD", "Core i5 7th Gen | 4GB RAM | 256GB SSD | detachable", "2-in-1", 15_500, ["Core i5 7th Gen", "4GB RAM", "256GB SSD", "Detachable"], "flex.png"),
    ("Dell Latitude 7390", "Core i5 8th Gen | 8GB RAM | 256GB SSD", "business", 22_000, ["Core i5 8th Gen", "8GB RAM", "256GB SSD"], "probook.png"),
    ("Lenovo ThinkPad E580 Core i3 8GB 256GB SSD", "Core i3 8th Gen | 8GB RAM | 256GB SSD | boxed", "business", 26_500, ["Core i3 8th Gen", "8GB RAM", "256GB SSD", "Boxed"], "probook.png"),
    ("Lenovo ThinkPad E590 Core i3 8GB 256GB SSD", "Core i3 10th Gen | 8GB RAM | 256GB SSD | boxed", "business", 29_500, ["Core i3 10th Gen", "8GB RAM", "256GB SSD", "Boxed"], "probook.png"),
    ("Lenovo ThinkPad L14 Ryzen 5", "Ryzen 5 | 16GB RAM | 256GB SSD", "business", 31_500, ["Ryzen 5", "16GB RAM", "256GB SSD"], "probook.png"),
    ("Lenovo ThinkPad L14 Ryzen 7", "Ryzen 7 | 16GB RAM | 256GB SSD", "business", 36_500, ["Ryzen 7", "16GB RAM", "256GB SSD"], "probook.png"),
    ("Dell Latitude 5430", "Core i7 12th Gen | 16GB RAM | 256GB SSD | touchscreen", "business", 41_000, ["Core i7 12th Gen", "16GB RAM", "256GB SSD", "Touchscreen"], "probook.png"),
    ("Asus ExpertBook B1500C", "Core i7 11th Gen | 16GB RAM | 512GB SSD", "business", 43_000, ["Core i7 11th Gen", "16GB RAM", "512GB SSD"], "probook.png"),
    ("Lenovo ThinkPad Yoga X13 Core i7", "Core i7 12th Gen | 32GB RAM | 256GB SSD | touchscreen", "2-in-1", 56_000, ["Core i7 12th Gen", "32GB RAM", "256GB SSD", "Touchscreen"], "flex.png"),
    ("HP ProBook 11 G11 Pentium", "Pentium 12th Gen | 8GB RAM | 128GB SSD", "business", 18_000, ["Pentium 12th Gen", "8GB RAM", "128GB SSD"], "probook.png"),
    ("HP ProBook 11 G11 Core i3 Stylus", "Core i3 12th Gen | 8GB RAM | 128GB SSD | stylus pen", "business", 23_000, ["Core i3 12th Gen", "8GB RAM", "128GB SSD", "Stylus pen"], "probook.png"),
    ("HP ProBook 440 G8", "Core i5 11th Gen | 8GB RAM | 256GB SSD", "business", 31_000, ["Core i5 11th Gen", "8GB RAM", "256GB SSD"], "probook.png"),
    ("HP EliteBook 840 G7 Touch", "Core i5 10th Gen | 16GB RAM | 256GB SSD | touchscreen", "business", 36_000, ["Core i5 10th Gen", "16GB RAM", "256GB SSD", "Touchscreen"], "probook.png"),
    ("HP EliteBook 840 G8 Core i5 16GB 256GB SSD", "Core i5 11th Gen | 16GB RAM | 256GB SSD", "business", 38_000, ["Core i5 11th Gen", "16GB RAM", "256GB SSD"], "probook.png"),
    ("HP EliteBook 840 G8 Core i5 Touch 16GB 256GB SSD", "Core i5 11th Gen | 16GB RAM | 256GB SSD | touchscreen", "business", 40_000, ["Core i5 11th Gen", "16GB RAM", "256GB SSD", "Touchscreen"], "probook.png"),
    ("HP EliteBook 840 G8 Core i5 16GB 512GB SSD", "Core i5 11th Gen | 16GB RAM | 512GB SSD", "business", 41_000, ["Core i5 11th Gen", "16GB RAM", "512GB SSD"], "probook.png"),
    ("HP ProBook 435 G8 x360 Ryzen 5", "Ryzen 5 | 16GB RAM | 256GB SSD | x360", "2-in-1", 38_000, ["Ryzen 5", "16GB RAM", "256GB SSD", "x360"], "flex.png"),
    ("HP EliteBook 830 G7 Core i7", "Core i7 10th Gen | 16GB RAM | 256GB SSD", "business", 41_000, ["Core i7 10th Gen", "16GB RAM", "256GB SSD"], "probook.png"),
    ("HP ProBook Aero 635 G8 Ryzen 7", "Ryzen 7 | 16GB RAM | 512GB SSD", "business", 41_000, ["Ryzen 7", "16GB RAM", "512GB SSD"], "probook.png"),
    ("HP ProBook 435 G7 x360 Ryzen 7", "Ryzen 7 | 16GB RAM | 512GB SSD | x360", "2-in-1", 43_000, ["Ryzen 7", "16GB RAM", "512GB SSD", "x360"], "flex.png"),
    ("HP EliteBook 830 G8 x360 Core i5", "Core i5 11th Gen | 16GB RAM | 256GB SSD | touchscreen", "2-in-1", 43_000, ["Core i5 11th Gen", "16GB RAM", "256GB SSD", "x360 touchscreen"], "flex.png"),
    ("HP ProBook 435 G8 x360 Ryzen 7", "Ryzen 7 | 16GB RAM | 512GB SSD | x360", "2-in-1", 46_000, ["Ryzen 7", "16GB RAM", "512GB SSD", "x360"], "flex.png"),
    ("HP EliteBook 840 G8 Core i7 16GB 512GB SSD", "Core i7 11th Gen | 16GB RAM | 512GB SSD", "business", 47_000, ["Core i7 11th Gen", "16GB RAM", "512GB SSD"], "probook.png"),
    ("HP ProBook 435 G9 x360 Ryzen 7", "Ryzen 7 | 16GB RAM | 512GB SSD | x360", "2-in-1", 48_000, ["Ryzen 7", "16GB RAM", "512GB SSD", "x360"], "flex.png"),
    ("HP EliteBook 830 G8 x360 Core i7", "Core i7 11th Gen | 16GB RAM | 512GB SSD | touchscreen", "2-in-1", 56_000, ["Core i7 11th Gen", "16GB RAM", "512GB SSD", "x360 touchscreen"], "flex.png"),
    ("Lenovo ThinkPad Yoga Celeron 4GB 128GB SSD", "Celeron | 4GB RAM | 128GB SSD | touchscreen | stylus", "2-in-1", 18_000, ["Celeron", "4GB RAM", "128GB SSD", "Touchscreen", "Stylus"], "flex.png"),
    ("NEC VersaPro Core i5 8th Gen", "Core i5 8th Gen | 8GB RAM | 256GB SSD", "business", 21_000, ["Core i5 8th Gen", "8GB RAM", "256GB SSD"], "probook.png"),
    ("Microsoft Surface Core m3 Detachable", "Core m3 | 8GB RAM | 128GB SSD | detachable touchscreen", "2-in-1", 25_000, ["Core m3", "8GB RAM", "128GB SSD", "Detachable touchscreen"], "flex.png"),
    ("Toshiba Dynabook Core i3 11th Gen", "Core i3 11th Gen | 8GB RAM | 256GB SSD", "business", 23_000, ["Core i3 11th Gen", "8GB RAM", "256GB SSD"], "probook.png"),
    ("Toshiba Core i7 8th Gen Touch 16GB 256GB SSD", "Core i7 8th Gen | 16GB RAM | 256GB SSD | touchscreen", "business", 28_000, ["Core i7 8th Gen", "16GB RAM", "256GB SSD", "Touchscreen"], "probook.png"),
    ("Toshiba Core i7 10th Gen Touch 16GB 256GB SSD", "Core i7 10th Gen | 16GB RAM | 256GB SSD | touchscreen", "business", 33_000, ["Core i7 10th Gen", "16GB RAM", "256GB SSD", "Touchscreen"], "probook.png"),
    ("Toshiba Core i7 11th Gen 16GB 256GB SSD", "Core i7 11th Gen | 16GB RAM | 256GB SSD", "business", 33_000, ["Core i7 11th Gen", "16GB RAM", "256GB SSD"], "probook.png"),
    ("Lenovo ThinkPad E580 Core i7 16GB 256GB SSD", "Core i7 8th Gen | 16GB RAM | 256GB SSD", "business", 30_500, ["Core i7 8th Gen", "16GB RAM", "256GB SSD"], "probook.png"),
    ("Lenovo ThinkPad E580 Core i7 16GB 512GB SSD", "Core i7 8th Gen | 16GB RAM | 512GB SSD", "business", 38_000, ["Core i7 8th Gen", "16GB RAM", "512GB SSD"], "probook.png"),
    ("Microsoft Surface Laptop 4 Ryzen 5", "Ryzen 5 | 16GB RAM | 256GB SSD | touchscreen", "business", 38_000, ["Ryzen 5", "16GB RAM", "256GB SSD", "Touchscreen"], "ultrabook.png"),
    ("Microsoft Surface Laptop 4 Core i7", "Core i7 11th Gen | 16GB RAM | 256GB SSD | touchscreen", "business", 48_000, ["Core i7 11th Gen", "16GB RAM", "256GB SSD", "Touchscreen"], "ultrabook.png"),
]


class Command(BaseCommand):
    help = "Add sample laptop inventory using supplied list prices plus KSh 3,000."

    def handle(self, *args, **options):
        created_count = 0
        for name, subtitle, category, price, specs, image_name in ROWS + ADDITIONAL_ROWS:
            if Product.objects.filter(name=name).exists():
                continue

            product = Product(
                name=name,
                subtitle=subtitle,
                category=category,
                price=price,
                compare_price=None,
                specs=specs,
                stock=5,
                badge="New arrival",
            )
            with (SAMPLE_IMAGES / image_name).open("rb") as image_file:
                product.image.save(image_name, File(image_file), save=True)
            created_count += 1

        self.stdout.write(self.style.SUCCESS(f"Added {created_count} sample products; existing matching products were kept."))
