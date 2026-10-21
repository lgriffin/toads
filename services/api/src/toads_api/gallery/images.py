"""Turn an uploaded photo into what the hub keeps: a web-sized WebP and a thumbnail.

Every photo is decoded and re-encoded, never stored as sent. That drops EXIF (a phone photo's GPS position goes with
it), turns the photo the right way up, and means the bytes the page serves are an image Pillow wrote, whatever the
upload claimed to be.
"""

from __future__ import annotations

import io
import warnings
from dataclasses import dataclass

from PIL import Image, ImageOps, UnidentifiedImageError

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
# Bigger than any phone or monitor screenshot; refuses decompression bombs before they are decoded.
MAX_PIXELS = 50_000_000
WEB_EDGE = 2048
THUMB_EDGE = 640
ACCEPTED = frozenset({"JPEG", "PNG", "WEBP", "GIF"})
MEDIA_TYPE = "image/webp"


class ImageRejected(Exception):
    """The upload is not a photo the hub keeps; the message says why, for the member."""


@dataclass(frozen=True)
class ProcessedImage:
    image: bytes
    thumbnail: bytes
    width: int
    height: int
    media_type: str = MEDIA_TYPE


def _webp(img: Image.Image, edge: int, quality: int) -> tuple[bytes, int, int]:
    copy = img.copy()
    copy.thumbnail((edge, edge), Image.Resampling.LANCZOS)
    out = io.BytesIO()
    copy.save(out, format="WEBP", quality=quality, method=4)
    return out.getvalue(), copy.width, copy.height


def process(raw: bytes) -> ProcessedImage:
    if not raw:
        raise ImageRejected("The photo is empty")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise ImageRejected(f"A photo is at most {MAX_UPLOAD_BYTES // (1024 * 1024)} MB")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            img = Image.open(io.BytesIO(raw))
            if img.format not in ACCEPTED:
                raise ImageRejected("Send a JPEG, PNG, WebP or GIF photo")
            if img.width * img.height > MAX_PIXELS:
                raise ImageRejected("That photo is too large")
            if getattr(img, "n_frames", 1) > 1:
                raise ImageRejected("Animated images are not supported; send a still photo")
            img.load()
    except ImageRejected:
        raise
    except (UnidentifiedImageError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise ImageRejected("That file is not a photo the hub can read") from None
    except (OSError, ValueError, SyntaxError):
        raise ImageRejected("That photo could not be read; it may be damaged") from None
    upright = ImageOps.exif_transpose(img)
    mode = "RGBA" if upright.mode in {"RGBA", "LA", "PA"} or "transparency" in upright.info else "RGB"
    clean = upright.convert(mode)
    image, width, height = _webp(clean, WEB_EDGE, 85)
    thumbnail, _, _ = _webp(clean, THUMB_EDGE, 75)
    return ProcessedImage(image=image, thumbnail=thumbnail, width=width, height=height)
