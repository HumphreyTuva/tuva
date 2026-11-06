"""Shrink uploaded product photos: resize and convert to WebP.

Phone photos and PNG screenshots are often 2 MB or more; the same picture as
a resized WebP is usually 50-150 KB. Used for new uploads (model save hooks
and the replace-image endpoint) and by the `optimize_media` command.
"""
import io
import os

from django.conf import settings
from django.core.files.base import ContentFile
from PIL import Image, ImageOps


def optimize_bytes(data):
    """Return (webp_bytes, original_format) or None if the data can't be improved."""
    max_side = getattr(settings, "IMAGE_MAX_SIDE", 1200)
    quality = getattr(settings, "IMAGE_QUALITY", 82)
    try:
        with Image.open(io.BytesIO(data)) as img:
            original_format = img.format
            img.load()
            img = ImageOps.exif_transpose(img)
            img.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
            has_alpha = img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info)
            img = img.convert("RGBA" if has_alpha else "RGB")
            out = io.BytesIO()
            img.save(out, "WEBP", quality=quality, method=4)
    except Exception:
        # Unreadable, corrupt or oversized-bomb image: leave it untouched.
        return None
    result = out.getvalue()
    if original_format == "WEBP" and len(result) >= len(data):
        return None
    return result, original_format


def optimize_upload(source, name=None):
    """Return a ContentFile (.webp) for an uploaded image, or None to keep the original."""
    if hasattr(source, "seek"):
        source.seek(0)
    data = source.read()
    if hasattr(source, "seek"):
        source.seek(0)
    optimized = optimize_bytes(data)
    if optimized is None:
        return None
    stem = os.path.splitext(os.path.basename(name or getattr(source, "name", "") or "image"))[0] or "image"
    return ContentFile(optimized[0], name=f"{stem}.webp")
