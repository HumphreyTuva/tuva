"""Shrink existing product photos (resize + convert to WebP).

Safe by design - nothing is changed unless you pass --apply:

  python manage.py optimize_media                  # dry run: shows the savings
  python manage.py optimize_media --apply          # writes new .webp files, updates the DB,
                                                   #   keeps the old files
  python manage.py optimize_media --orphans        # dry run: lists old files nothing uses
  python manage.py optimize_media --orphans --apply   # deletes those old files

Recommended order: back up, dry run, --apply, check the site, then
--orphans (look at the list), then --orphans --apply to free the space.
"""
import os

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from shop.imageopt import optimize_bytes
from shop.models import Product, ProductImage


def human(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.1f} {unit}" if unit != "B" else f"{n} B"
        n /= 1024


class Command(BaseCommand):
    help = "Resize and convert existing product images to WebP (dry run unless --apply)."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Actually make the changes.")
        parser.add_argument("--orphans", action="store_true",
                            help="List (or with --apply, delete) image files no product uses.")

    def handle(self, *args, **opts):
        if opts["orphans"]:
            return self.handle_orphans(opts["apply"])
        return self.handle_convert(opts["apply"])

    def _rows(self):
        for model in (Product, ProductImage):
            for obj in model.objects.exclude(image="").order_by("pk"):
                yield model, obj

    def handle_convert(self, apply):
        total_before = total_after = converted = skipped = 0
        for model, obj in self._rows():
            field = obj.image
            label = f"{model.__name__} #{obj.pk} {field.name}"
            try:
                with field.storage.open(field.name, "rb") as fh:
                    data = fh.read()
            except (FileNotFoundError, OSError):
                self.stdout.write(self.style.WARNING(f"MISSING  {label}"))
                skipped += 1
                continue
            result = optimize_bytes(data)
            if result is None or len(result[0]) >= len(data):
                self.stdout.write(f"skip     {label} (already small or unreadable)")
                skipped += 1
                continue
            new_data = result[0]
            total_before += len(data)
            total_after += len(new_data)
            converted += 1
            self.stdout.write(f"convert  {label}: {human(len(data))} -> {human(len(new_data))}")
            if apply:
                stem = os.path.splitext(field.name)[0]
                new_name = field.storage.save(f"{stem}.webp", ContentFile(new_data))
                # .update() avoids model save hooks (no re-optimising, no re-embedding).
                model.objects.filter(pk=obj.pk).update(image=new_name)

        self.stdout.write("")
        self.stdout.write(f"{converted} converted, {skipped} skipped")
        self.stdout.write(f"Total: {human(total_before)} -> {human(total_after)} "
                          f"(saves {human(total_before - total_after)})")
        if apply:
            self.stdout.write(self.style.SUCCESS(
                "Done. Old files were kept. Check the site, then run: "
                "python manage.py optimize_media --orphans"))
        else:
            self.stdout.write(self.style.WARNING("Dry run only - nothing changed. Add --apply to proceed."))

    def handle_orphans(self, apply):
        storage = Product._meta.get_field("image").storage
        used = {obj.image.name for _, obj in self._rows()}
        freed = count = 0
        for folder in ("products",):
            if not storage.exists(folder):
                continue
            for name in sorted(storage.listdir(folder)[1]):
                path = f"{folder}/{name}"
                if path in used:
                    continue
                size = storage.size(path)
                freed += size
                count += 1
                self.stdout.write(f"{'delete' if apply else 'unused'}  {path} ({human(size)})")
                if apply:
                    storage.delete(path)
        self.stdout.write("")
        self.stdout.write(f"{count} unused files, {human(freed)} {'freed' if apply else 'could be freed'}")
        if not apply:
            self.stdout.write(self.style.WARNING("Dry run only - nothing deleted. Add --apply to delete."))
