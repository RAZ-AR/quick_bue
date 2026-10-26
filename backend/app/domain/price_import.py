"""Price list import: guess columns, read cells, plan what changes in the seller's catalog.

Pure functions: no database. A row is matched to a product by SKU (the code in the seller's accounting,
e.g. ArmSoft), or by exact name when the file has no SKU column or the product has no SKU yet.
Uploading the same file twice changes nothing.
"""

import re
import uuid
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from enum import StrEnum

from app.models import Unit

MAX_ROWS = 5000
PRICE_JUMP = Decimal("0.5")  # a price moving by more than 50% is likely a wrong column


class Field(StrEnum):
    sku = "sku"
    name_hy = "name_hy"
    name_ru = "name_ru"
    name_en = "name_en"
    price = "price"
    unit = "unit"
    in_stock = "in_stock"
    stock_qty = "stock_qty"  # a quantity left: in stock when above zero
    min_qty = "min_qty"
    pack_size = "pack_size"


NAME_FIELDS = {Field.name_hy: "hy", Field.name_ru: "ru", Field.name_en: "en"}

# Header words in Armenian, Russian and English, including ArmSoft export headers
_SYNONYMS: list[tuple[Field, tuple[str, ...]]] = [
    (Field.sku, ("артикул", "код", "code", "sku", "article", "արտիկուլ", "կոդ", "ծածկագիր")),
    (Field.price, ("цена", "стоимость", "price", "գին")),
    (Field.unit, ("ед", "единиц", "unit", "uom", "միավոր", "չափ")),
    (Field.stock_qty, ("остаток", "склад", "stock qty", "quantity", "մնացորդ", "պահեստ")),
    (Field.in_stock, ("наличи", "in stock", "available", "availability", "առկա")),
    (Field.min_qty, ("мин", "min", "նվազ")),
    (Field.pack_size, ("фасовк", "упаковк", "pack", "փաթեթ")),
    (Field.name_ru, ("наименование", "название", "товар", "name", "product", "անվանում", "ապրանք")),
]

_UNITS = {
    Unit.kg: ("kg", "кг", "կգ", "килограмм", "kilogram"),
    Unit.l: ("l", "л", "լ", "литр", "liter", "litre", "lt"),
    Unit.pcs: ("pcs", "шт", "штука", "հատ", "pc", "piece", "pieces", "ea"),
    Unit.pack: ("pack", "уп", "упак", "упаковка", "տուփ", "փաթեթ", "box", "кор", "коробка", "ящик"),
}
_YES = {"1", "да", "yes", "y", "true", "+", "есть", "в наличии", "այո", "առկա է", "v", "✓"}
_NO = {"0", "нет", "no", "n", "false", "-", "—", "нет в наличии", "ոչ", "չկա"}


def _norm(text: object) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip().lower()


def _script(values: list[str]) -> str | None:
    """Which language a column of names is in, by its letters."""
    joined = "".join(values)
    counts = {
        "hy": len(re.findall(r"[Ա-֏]", joined)),
        "ru": len(re.findall(r"[а-яё]", joined, re.I)),
        "en": len(re.findall(r"[a-z]", joined, re.I)),
    }
    best = max(counts, key=lambda k: counts[k])
    return best if counts[best] else None


def guess_mapping(headers: list[str], rows: list[list[str]]) -> dict[int, Field]:
    """Column index → field, from header words; name columns get their language from the letters inside."""
    mapping: dict[int, Field] = {}
    taken: set[Field] = set()
    for i, header in enumerate(headers):
        h = _norm(header)
        if not h:
            continue
        for f, words in _SYNONYMS:
            if any(w in h for w in words):
                if f == Field.name_ru:  # a name column: pick the language
                    lang_hint = (
                        "hy"
                        if any(w in h for w in ("арм", "hy", "հայ", "arm"))
                        else "en"
                        if any(w in h for w in ("англ", "en", "eng", "անգլ"))
                        else "ru"
                        if any(w in h for w in ("рус", "ru", "ռուս"))
                        else _script([r[i] for r in rows[:30] if i < len(r)])
                    )
                    f = {"hy": Field.name_hy, "en": Field.name_en}.get(lang_hint or "ru", Field.name_ru)
                if f not in taken:
                    mapping[i] = f
                    taken.add(f)
                break
    return mapping


def parse_amount(raw: object) -> Decimal | None:
    """'3 500', '3500.00', '3,500 ֏', '3 500,50' → Decimal; None when empty or not a number."""
    if raw is None:
        return None
    if isinstance(raw, int | float | Decimal):
        return Decimal(str(raw))
    s = re.sub(r"[^\d,.\-]", "", str(raw).replace(" ", " ").replace(" ", ""))
    if not s or s in "-,.":
        return None
    if "," in s and "." in s:  # the last one is the decimal mark
        s = s.replace(",", "") if s.rfind(".") > s.rfind(",") else s.replace(".", "").replace(",", ".")
    elif "," in s:
        head, _, tail = s.rpartition(",")
        s = s.replace(",", "") if len(tail) == 3 and head else s.replace(",", ".")
    try:
        return Decimal(s)
    except InvalidOperation:
        return None


def parse_price(raw: object) -> int | None:
    value = parse_amount(raw)
    if value is None:
        return None
    return int(value.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def parse_unit(raw: object) -> Unit | None:
    s = _norm(raw).rstrip(".")
    for unit, words in _UNITS.items():
        if s in words:
            return unit
    return None


def parse_bool(raw: object) -> bool | None:
    s = _norm(raw)
    if s in _YES:
        return True
    if s in _NO:
        return False
    return None


# --- the plan -----------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Existing:
    """What the import needs to know about a product already in the catalog."""

    id: uuid.UUID
    sku: str | None
    name: dict[str, str]
    price_amd: int
    unit: Unit
    in_stock: bool
    min_qty: Decimal
    pack_size: str | None
    archived: bool
    top_tier_price_amd: int | None = None  # the highest volume price, which must stay below the list price


@dataclass
class Row:
    """One file row read through the mapping. None = the column is not mapped or the cell is empty."""

    line: int  # row number in the file, for messages (header = 1)
    sku: str | None = None
    name: dict[str, str] = field(default_factory=dict)
    price_amd: int | None = None
    unit: Unit | None = None
    in_stock: bool | None = None
    min_qty: Decimal | None = None
    pack_size: str | None = None
    problems: list[str] = field(default_factory=list)


class Action(StrEnum):
    create = "create"
    update = "update"
    same = "same"
    error = "error"
    out_of_stock = "out_of_stock"  # in the catalog, missing from the file (option)


@dataclass
class Change:
    field: str
    old: object
    new: object


@dataclass
class Item:
    action: Action
    line: int | None
    row: Row | None
    product_id: uuid.UUID | None = None
    changes: list[Change] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def read_row(line: int, cells: list[object], mapping: dict[int, Field]) -> Row | None:
    """Cells of one row → Row; None for an empty row."""
    if not any(_norm(c) for c in cells):
        return None
    row = Row(line=line)
    for i, f in mapping.items():
        raw = cells[i] if i < len(cells) else None
        if raw is None or _norm(raw) == "":
            continue
        text = re.sub(r"\s+", " ", str(raw)).strip()
        if f == Field.sku:
            # Excel turns codes into numbers: 1001.0 → "1001"
            row.sku = text[:-2] if re.fullmatch(r"\d+\.0", text) else text[:64]
        elif f in NAME_FIELDS:
            row.name[NAME_FIELDS[f]] = text[:200]
        elif f == Field.price:
            row.price_amd = parse_price(raw)
            if row.price_amd is None or row.price_amd <= 0:
                row.problems.append("bad_price")
        elif f == Field.unit:
            row.unit = parse_unit(raw)
            if row.unit is None:
                row.problems.append("bad_unit")
        elif f == Field.in_stock:
            row.in_stock = parse_bool(raw)
            if row.in_stock is None:
                row.problems.append("bad_in_stock")
        elif f == Field.stock_qty:
            qty = parse_amount(raw)
            if qty is None:
                row.problems.append("bad_qty")
            else:
                row.in_stock = qty > 0
        elif f == Field.min_qty:
            row.min_qty = parse_amount(raw)
            if row.min_qty is None or row.min_qty <= 0:
                row.problems.append("bad_qty")
        elif f == Field.pack_size:
            row.pack_size = text[:40]
    return row


def _key(name: dict[str, str]) -> set[str]:
    return {_norm(v) for v in name.values() if v}


def plan(
    rows: list[Row],
    existing: list[Existing],
    default_unit: Unit | None = None,
    missing_out_of_stock: bool = False,
) -> list[Item]:
    """What the import will do with every row, and with catalog products the file does not mention."""
    by_sku = {p.sku.lower(): p for p in existing if p.sku}
    by_name: dict[str, Existing] = {}
    for p in existing:
        for k in _key(p.name):
            by_name.setdefault(k, p)
    seen_sku: set[str] = set()
    touched: set[uuid.UUID] = set()
    items: list[Item] = []

    for row in rows:
        problems = list(row.problems)
        if row.sku:
            if row.sku.lower() in seen_sku:
                problems.append("duplicate_sku")
            seen_sku.add(row.sku.lower())
        match = by_sku.get(row.sku.lower()) if row.sku else None
        if match is None:
            # By name: always without a code; with a code only for products that have none yet (first import)
            named = next((by_name[k] for k in _key(row.name) if k in by_name), None)
            if named is not None and (not row.sku or not named.sku):
                match = named
        if match is not None and match.id in touched:
            problems.append("duplicate_row")
        if problems:
            items.append(Item(Action.error, row.line, row, match.id if match else None, problems=problems))
            continue

        if match is None:
            unit = row.unit or default_unit
            missing = [
                code
                for code, ok in (("no_name", row.name), ("no_price", row.price_amd), ("no_unit", unit))
                if not ok
            ]
            if missing:
                items.append(Item(Action.error, row.line, row, problems=missing))
                continue
            items.append(Item(Action.create, row.line, row))
            continue

        touched.add(match.id)
        changes: list[Change] = []
        warnings: list[str] = []
        if row.price_amd is not None and row.price_amd != match.price_amd:
            changes.append(Change("price_amd", match.price_amd, row.price_amd))
            if abs(Decimal(row.price_amd - match.price_amd)) > match.price_amd * PRICE_JUMP:
                warnings.append("price_jump")
            if match.top_tier_price_amd is not None and row.price_amd <= match.top_tier_price_amd:
                warnings.append("tiers_above_price")
        merged = {**match.name, **row.name}
        if merged != match.name:
            changes.append(Change("name", match.name, merged))
        for attr in ("unit", "in_stock", "min_qty", "pack_size"):
            new = getattr(row, attr)
            if new is not None and new != getattr(match, attr):
                changes.append(Change(attr, getattr(match, attr), new))
        if row.sku and row.sku != match.sku:  # matched by name: remember the code
            changes.append(Change("sku", match.sku, row.sku))
        if match.archived:
            changes.append(Change("archived", True, False))
        action = Action.update if changes else Action.same
        items.append(Item(action, row.line, row, match.id, changes, warnings=warnings))

    if missing_out_of_stock:
        for p in existing:
            if p.id not in touched and not p.archived and p.in_stock:
                items.append(Item(Action.out_of_stock, None, None, p.id, [Change("in_stock", True, False)]))
    return items
