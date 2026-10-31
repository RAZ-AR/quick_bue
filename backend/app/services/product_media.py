"""Photos and documents of a seller's product.

Photos are re-encoded on the server: a large WebP for the product card and a small one for lists, with EXIF
(location, camera) dropped. The first photo is the main one; the seller may keep a photo hidden from buyers.
Documents (certificates, declarations) are kept as uploaded; buyers who signed in can open them,
guests only see that they exist.
"""

import io
import uuid
from datetime import date

from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Product, ProductDocKind, ProductDocument
from app.platform import storage
from app.platform.authz import Actor
from app.platform.errors import NotFound, ValidationFailed
from app.services.seller_catalog import _own, _seller

MAX_IMAGES = 6
MAX_IMAGE_MB = 12
MAX_DOC_MB = 10
LARGE, SMALL = 1600, 480
IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
DOC_TYPES = {"application/pdf", "image/jpeg", "image/png", "image/webp"}


def thumb_key(key: str) -> str:
    return key.removesuffix(".webp") + "-s.webp"


def image_urls(product: Product, *, public: bool = True) -> list[dict]:
    """Photos for buyers (hidden ones left out) or, with public=False, all of them for the seller."""
    hidden = set(product.hidden_images or [])
    return [
        {"url": f"/media/{k}", "thumb": f"/media/{thumb_key(k)}", "shown": k not in hidden}
        for k in product.images or []
        if not (public and k in hidden)
    ]


def _webp(img: Image.Image, size: int, quality: int) -> bytes:
    copy = img.copy()
    copy.thumbnail((size, size), Image.Resampling.LANCZOS)
    out = io.BytesIO()
    copy.save(out, "WEBP", quality=quality, method=5)
    return out.getvalue()


async def add_image(
    session: AsyncSession, actor: Actor, product_id: uuid.UUID, data: bytes, content_type: str
) -> Product:
    actor = _seller(actor)
    product = await _own(session, actor, product_id)
    if len(product.images or []) >= MAX_IMAGES:
        raise ValidationFailed([{"field": "images", "code": "too_many_images", "max": MAX_IMAGES}])
    if content_type not in IMAGE_TYPES:
        raise ValidationFailed([{"field": "images", "code": "file_type_not_allowed"}])
    if not data or len(data) > MAX_IMAGE_MB * 1024 * 1024:
        raise ValidationFailed([{"field": "images", "code": "file_too_large", "max_mb": MAX_IMAGE_MB}])
    try:
        img = Image.open(io.BytesIO(data))
        img = ImageOps.exif_transpose(img).convert("RGB")  # turn phone photos upright, drop EXIF
    except (UnidentifiedImageError, OSError) as e:
        raise ValidationFailed([{"field": "images", "code": "bad_image"}]) from e
    key = f"products/{product.id}/{uuid.uuid4().hex}.webp"
    storage.save_as(key, _webp(img, LARGE, 82))
    storage.save_as(thumb_key(key), _webp(img, SMALL, 78))
    product.images = [*(product.images or []), key]
    return product


def _image_at(product: Product, index: int) -> str:
    images = product.images or []
    if not 0 <= index < len(images):
        raise NotFound("image_not_found")
    return images[index]


async def remove_image(session: AsyncSession, actor: Actor, product_id: uuid.UUID, index: int) -> Product:
    actor = _seller(actor)
    product = await _own(session, actor, product_id)
    key = _image_at(product, index)
    product.images = [k for k in product.images if k != key]
    product.hidden_images = [k for k in product.hidden_images or [] if k != key]
    storage.delete(key)
    storage.delete(thumb_key(key))
    return product


async def make_main(session: AsyncSession, actor: Actor, product_id: uuid.UUID, index: int) -> Product:
    actor = _seller(actor)
    product = await _own(session, actor, product_id)
    key = _image_at(product, index)
    product.images = [key, *(k for k in product.images if k != key)]
    product.hidden_images = [k for k in product.hidden_images or [] if k != key]  # the main photo is shown
    return product


async def show_image(
    session: AsyncSession, actor: Actor, product_id: uuid.UUID, index: int, shown: bool
) -> Product:
    actor = _seller(actor)
    product = await _own(session, actor, product_id)
    key = _image_at(product, index)
    rest = [k for k in product.hidden_images or [] if k != key]
    product.hidden_images = rest if shown else [*rest, key]
    return product


async def add_document(
    session: AsyncSession,
    actor: Actor,
    product_id: uuid.UUID,
    kind: ProductDocKind,
    data: bytes,
    content_type: str,
    file_name: str,
    number: str | None = None,
    valid_until: date | None = None,
) -> ProductDocument:
    actor = _seller(actor)
    product = await _own(session, actor, product_id)
    if content_type not in DOC_TYPES:
        raise ValidationFailed([{"field": "documents", "code": "file_type_not_allowed"}])
    if not data or len(data) > MAX_DOC_MB * 1024 * 1024:
        raise ValidationFailed([{"field": "documents", "code": "file_too_large", "max_mb": MAX_DOC_MB}])
    key = storage.save(data, f"products/{product.id}/docs", content_type)
    doc = ProductDocument(
        product_id=product.id,
        kind=kind,
        number=(number or "").strip()[:80] or None,
        valid_until=valid_until,
        storage_key=key,
        content_type=content_type,
        original_name=(file_name or "")[:200] or None,
    )
    session.add(doc)
    await session.flush()
    return doc


async def remove_document(
    session: AsyncSession, actor: Actor, product_id: uuid.UUID, doc_id: uuid.UUID
) -> None:
    actor = _seller(actor)
    product = await _own(session, actor, product_id)
    doc = await session.get(ProductDocument, doc_id)
    if doc is None or doc.product_id != product.id:
        raise NotFound("document_not_found")
    storage.delete(doc.storage_key)
    await session.delete(doc)
