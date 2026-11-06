import io
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from PIL import Image

from .imageopt import optimize_upload
from .models import Product


def make_png(size=(2400, 1800)):
    # Noisy-ish gradient so the PNG is genuinely large.
    img = Image.effect_noise(size, 60).convert("RGB")
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


class ImageOptimizeTests(TestCase):
    def setUp(self):
        self.media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media, True)
        self.override = override_settings(MEDIA_ROOT=self.media)
        self.override.enable()
        self.addCleanup(self.override.disable)

    def test_upload_is_resized_and_converted(self):
        data = make_png()
        out = optimize_upload(SimpleUploadedFile("big.png", data, "image/png"))
        self.assertTrue(out.name.endswith(".webp"))
        self.assertLess(len(out.read()), len(data))
        out.seek(0)
        with Image.open(out) as img:
            self.assertEqual(img.format, "WEBP")
            self.assertLessEqual(max(img.size), 1200)

    def test_corrupt_upload_is_left_alone(self):
        self.assertIsNone(optimize_upload(SimpleUploadedFile("x.png", b"not an image")))

    def test_saving_a_product_stores_webp(self):
        product = Product.objects.create(
            name="Test", category="laptop", price=100,
            image=SimpleUploadedFile("big.png", make_png(), "image/png"),
        )
        self.assertTrue(product.image.name.endswith(".webp"))
        self.assertTrue(product.image.storage.exists(product.image.name))

    def test_command_dry_run_then_apply_then_orphans(self):
        product = Product.objects.create(name="Old", category="laptop", price=100)
        # Store a big PNG directly, bypassing the save hook, like a pre-existing photo.
        product.image.save("old.png", SimpleUploadedFile("old.png", make_png()), save=False)
        Product.objects.filter(pk=product.pk).update(image=product.image.name)
        old_name = product.image.name

        call_command("optimize_media", stdout=io.StringIO())  # dry run
        product.refresh_from_db()
        self.assertEqual(product.image.name, old_name)

        call_command("optimize_media", "--apply", stdout=io.StringIO())
        product.refresh_from_db()
        self.assertTrue(product.image.name.endswith(".webp"))
        self.assertTrue(product.image.storage.exists(old_name))  # old kept

        call_command("optimize_media", "--orphans", stdout=io.StringIO())  # dry run
        self.assertTrue(product.image.storage.exists(old_name))
        call_command("optimize_media", "--orphans", "--apply", stdout=io.StringIO())
        self.assertFalse(product.image.storage.exists(old_name))
        self.assertTrue(product.image.storage.exists(product.image.name))
