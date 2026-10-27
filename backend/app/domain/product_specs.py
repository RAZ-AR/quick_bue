"""What a product card tells about the goods: characteristics by category, and the documents that prove them.

Built from what EAEU labelling requires (TR CU 022/2011: producer, country, shelf life, storage conditions,
composition, conformity; TR CU 034/2013 for meat: thermal state) and from what HoReCa buyers ask a supplier.
One source for the server (validation) and the app (GET /product-specs builds the form and the card).
"""

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from enum import StrEnum

T = dict[str, str]  # {"hy": ..., "ru": ..., "en": ...}


def _t(hy: str, ru: str, en: str) -> T:
    return {"hy": hy, "ru": ru, "en": en}


class Kind(StrEnum):
    text = "text"
    number = "number"
    choice = "choice"
    flag = "flag"


@dataclass(frozen=True)
class Spec:
    code: str
    kind: Kind
    label: T
    group: str  # origin | storage | product | pack
    unit: T | None = None
    options: dict[str, T] = field(default_factory=dict)
    categories: tuple[str, ...] = ()  # empty: every category (goods, not services)


GROUPS: dict[str, T] = {
    "product": _t("Ապրանք", "Товар", "Product"),
    "origin": _t("Ծագում", "Происхождение", "Origin"),
    "storage": _t("Պահպանում", "Хранение", "Storage"),
    "pack": _t("Փաթեթավորում", "Упаковка", "Packaging"),
}

COUNTRIES = {
    "AM": _t("Հայաստան", "Армения", "Armenia"),
    "RU": _t("Ռուսաստան", "Россия", "Russia"),
    "GE": _t("Վրաստան", "Грузия", "Georgia"),
    "IR": _t("Իրան", "Иран", "Iran"),
    "BY": _t("Բելառուս", "Беларусь", "Belarus"),
    "KZ": _t("Ղազախստան", "Казахстан", "Kazakhstan"),
    "TR": _t("Թուրքիա", "Турция", "Türkiye"),
    "CN": _t("Չինաստան", "Китай", "China"),
    "IT": _t("Իտալիա", "Италия", "Italy"),
    "DE": _t("Գերմանիա", "Германия", "Germany"),
    "NL": _t("Նիդեռլանդներ", "Нидерланды", "Netherlands"),
    "FR": _t("Ֆրանսիա", "Франция", "France"),
    "ES": _t("Իսպանիա", "Испания", "Spain"),
    "BR": _t("Բրազիլիա", "Бразилия", "Brazil"),
    "AR": _t("Արգենտինա", "Аргентина", "Argentina"),
    "other": _t("Այլ", "Другая", "Other"),
}

FOOD = ("dairy", "meat", "produce", "grocery", "coffee", "bakery")

SPECS: tuple[Spec, ...] = (
    # --- origin: who made it and where
    Spec("producer", Kind.text, _t("Արտադրող", "Производитель", "Producer"), "origin"),
    Spec("brand", Kind.text, _t("Ապրանքանիշ", "Бренд", "Brand"), "origin"),
    Spec(
        "country",
        Kind.choice,
        _t("Արտադրման երկիր", "Страна производства", "Country of origin"),
        "origin",
        options=COUNTRIES,
    ),
    Spec(
        "supply",
        Kind.choice,
        _t("Արտադրություն", "Производство", "Production"),
        "origin",
        options={
            "own": _t("Սեփական", "Собственное", "Own"),
            "partner": _t("Գործընկեր արտադրող", "Партнёр-производитель", "Partner producer"),
            "import": _t("Ներմուծում", "Импорт", "Import"),
        },
    ),
    # --- the product itself
    Spec(
        "animal",
        Kind.choice,
        _t("Կենդանի", "Вид мяса", "Animal"),
        "product",
        categories=("meat",),
        options={
            "beef": _t("Տավար", "Говядина", "Beef"),
            "veal": _t("Հորթ", "Телятина", "Veal"),
            "pork": _t("Խոզ", "Свинина", "Pork"),
            "lamb": _t("Գառ", "Баранина", "Lamb"),
            "chicken": _t("Հավ", "Курица", "Chicken"),
            "turkey": _t("Հնդկահավ", "Индейка", "Turkey"),
            "rabbit": _t("Ճագար", "Кролик", "Rabbit"),
            "other": _t("Այլ", "Другое", "Other"),
        },
    ),
    # TR CU 034/2013 thermal states
    Spec(
        "thermal",
        Kind.choice,
        _t("Ջերմային վիճակ", "Термическое состояние", "Thermal state"),
        "product",
        categories=("meat",),
        options={
            "fresh": _t("Թարմ (պարնոյ)", "Парное", "Fresh (warm)"),
            "cooled": _t("Սառեցված (օստիվշի)", "Остывшее", "Cooled"),
            "chilled": _t("Պաղեցված", "Охлаждённое", "Chilled"),
            "superchilled": _t("Թեթև սառեցված", "Подмороженное", "Superchilled"),
            "frozen": _t("Սառեցված", "Замороженное", "Frozen"),
            "deep_frozen": _t("Խորը սառեցված", "Глубокозамороженное", "Deep-frozen"),
        },
    ),
    Spec("cut", Kind.text, _t("Մաս / կտրվածք", "Часть туши / отруб", "Cut"), "product", categories=("meat",)),
    Spec(
        "bone",
        Kind.choice,
        _t("Ոսկոր", "Кость", "Bone"),
        "product",
        categories=("meat",),
        options={
            "bone_in": _t("Ոսկորով", "На кости", "Bone-in"),
            "boneless": _t("Առանց ոսկորի", "Без кости", "Boneless"),
        },
    ),
    Spec("halal", Kind.flag, _t("Հալալ", "Халяль", "Halal"), "product", categories=("meat",)),
    Spec(
        "milk",
        Kind.choice,
        _t("Կաթ", "Молоко", "Milk"),
        "product",
        categories=("dairy",),
        options={
            "cow": _t("Կովի", "Коровье", "Cow"),
            "sheep": _t("Ոչխարի", "Овечье", "Sheep"),
            "goat": _t("Այծի", "Козье", "Goat"),
            "buffalo": _t("Գոմեշի", "Буйволиное", "Buffalo"),
            "mixed": _t("Խառը", "Смешанное", "Mixed"),
        },
    ),
    Spec(
        "fat",
        Kind.number,
        _t("Յուղայնություն", "Жирность", "Fat"),
        "product",
        unit=_t("%", "%", "%"),
        categories=("dairy", "meat"),
    ),
    Spec("aging", Kind.text, _t("Հնեցում", "Выдержка", "Aging"), "product", categories=("dairy",)),
    Spec(
        "grade",
        Kind.choice,
        _t("Տեսակ", "Сорт", "Grade"),
        "product",
        categories=("produce", "meat"),
        options={
            "premium": _t("Բարձր", "Высший", "Premium"),
            "first": _t("Առաջին", "Первый", "First"),
            "second": _t("Երկրորդ", "Второй", "Second"),
        },
    ),
    Spec(
        "grown",
        Kind.choice,
        _t("Աճեցում", "Выращивание", "Grown"),
        "product",
        categories=("produce",),
        options={
            "open": _t("Բաց գրունտ", "Открытый грунт", "Open field"),
            "greenhouse": _t("Ջերմատուն", "Теплица", "Greenhouse"),
        },
    ),
    Spec("organic", Kind.flag, _t("Օրգանական", "Органик", "Organic"), "product", categories=FOOD),
    Spec(
        "coffee",
        Kind.choice,
        _t("Սուրճի տեսակ", "Сорт кофе", "Coffee"),
        "product",
        categories=("coffee",),
        options={
            "arabica": _t("Արաբիկա 100%", "Арабика 100%", "Arabica 100%"),
            "robusta": _t("Ռոբուստա", "Робуста", "Robusta"),
            "blend": _t("Խառնուրդ", "Смесь", "Blend"),
        },
    ),
    Spec(
        "roast",
        Kind.choice,
        _t("Բովում", "Обжарка", "Roast"),
        "product",
        categories=("coffee",),
        options={
            "light": _t("Թեթև", "Светлая", "Light"),
            "medium": _t("Միջին", "Средняя", "Medium"),
            "dark": _t("Մուգ", "Тёмная", "Dark"),
        },
    ),
    Spec(
        "form",
        Kind.choice,
        _t("Տեսք", "Вид", "Form"),
        "product",
        categories=("coffee",),
        options={
            "beans": _t("Հատիկներ", "Зерно", "Beans"),
            "ground": _t("Աղացած", "Молотый", "Ground"),
            "capsules": _t("Պատիճներ", "Капсулы", "Capsules"),
        },
    ),
    Spec("composition", Kind.text, _t("Բաղադրություն", "Состав", "Composition"), "product", categories=FOOD),
    Spec(
        "material",
        Kind.choice,
        _t("Նյութ", "Материал", "Material"),
        "product",
        categories=("disposables",),
        options={
            "paper": _t("Թուղթ", "Бумага", "Paper"),
            "kraft": _t("Կրաֆտ", "Крафт", "Kraft"),
            "pp": _t("Պլաստիկ PP", "Пластик PP", "Plastic PP"),
            "pet": _t("Պլաստիկ PET", "Пластик PET", "Plastic PET"),
            "ps": _t("Պլաստիկ PS", "Пластик PS", "Plastic PS"),
            "bagasse": _t("Բագաս", "Багасса", "Bagasse"),
            "aluminium": _t("Ալյումին", "Алюминий", "Aluminium"),
            "wood": _t("Փայտ", "Дерево", "Wood"),
        },
    ),
    Spec(
        "volume",
        Kind.number,
        _t("Ծավալ", "Объём", "Volume"),
        "product",
        unit=_t("մլ", "мл", "ml"),
        categories=("disposables", "cleaning"),
    ),
    Spec(
        "purpose",
        Kind.text,
        _t("Նշանակություն", "Назначение", "Purpose"),
        "product",
        categories=("cleaning",),
    ),
    Spec(
        "concentrate",
        Kind.flag,
        _t("Խտանյութ", "Концентрат", "Concentrate"),
        "product",
        categories=("cleaning",),
    ),
    # --- storage
    Spec(
        "storage",
        Kind.choice,
        _t("Պահպանման պայմաններ", "Условия хранения", "Storage"),
        "storage",
        categories=FOOD,
        options={
            "ambient": _t("Սենյակային ջերմաստիճան", "При комнатной температуре", "Ambient"),
            "chilled": _t("Սառնարան 0…+6 °C", "В холодильнике 0…+6 °C", "Chilled 0…+6 °C"),
            "frozen": _t("Սառցարան −18 °C", "В морозильнике −18 °C", "Frozen −18 °C"),
        },
    ),
    Spec(
        "shelf_life",
        Kind.number,
        _t("Պիտանիության ժամկետ", "Срок годности", "Shelf life"),
        "storage",
        unit=_t("օր", "дн.", "days"),
        categories=FOOD,
    ),
    # --- packaging
    Spec("net", Kind.text, _t("Զուտ քաշ / ծավալ", "Масса / объём нетто", "Net weight / volume"), "pack"),
    Spec(
        "per_pack",
        Kind.number,
        _t("Հատ տուփում", "Штук в упаковке", "Pieces per pack"),
        "pack",
        categories=("disposables", "grocery", "cleaning"),
    ),
    Spec("barcode", Kind.text, _t("Շտրիխկոդ", "Штрихкод", "Barcode"), "pack"),
)

BY_CODE = {s.code: s for s in SPECS}


class DocKind(StrEnum):
    """Documents a buyer may ask for (EAEU conformity, vet and phyto control, halal)."""

    declaration = "declaration"  # EAEU declaration of conformity
    certificate = "certificate"  # EAEU certificate of conformity
    veterinary = "veterinary"
    phytosanitary = "phytosanitary"
    halal = "halal"
    quality = "quality"  # quality certificate / lab test
    other = "other"


DOC_LABELS: dict[str, T] = {
    "declaration": _t(
        "ԵԱՏՄ համապատասխանության հայտարարագիր", "Декларация соответствия ЕАЭС", "EAEU declaration"
    ),
    "certificate": _t(
        "ԵԱՏՄ համապատասխանության սերտիֆիկատ", "Сертификат соответствия ЕАЭС", "EAEU certificate"
    ),
    "veterinary": _t("Անասնաբուժական վկայական", "Ветеринарное свидетельство", "Veterinary certificate"),
    "phytosanitary": _t(
        "Բուսասանիտարական վկայական", "Фитосанитарный сертификат", "Phytosanitary certificate"
    ),
    "halal": _t("Հալալ սերտիֆիկատ", "Сертификат халяль", "Halal certificate"),
    "quality": _t("Որակի վկայական", "Удостоверение качества", "Quality certificate"),
    "other": _t("Այլ փաստաթուղթ", "Другой документ", "Other document"),
}


def specs_for(category: str | None, is_service: bool) -> list[Spec]:
    """Characteristics a product of this category can have; services have none (a description is enough)."""
    if is_service:
        return []
    return [s for s in SPECS if not s.categories or (category is not None and category in s.categories)]


def clean(values: dict, category: str | None, is_service: bool) -> tuple[dict, list[dict]]:
    """Keep known characteristics of this category with valid values; empty values are dropped."""
    allowed = {s.code: s for s in specs_for(category, is_service)}
    out: dict = {}
    problems: list[dict] = []
    for code, raw in (values or {}).items():
        spec = allowed.get(code)
        if spec is None or raw is None or raw == "" or raw is False:
            continue
        if spec.kind == Kind.flag:
            out[code] = bool(raw)
        elif spec.kind == Kind.choice:
            if str(raw) in spec.options:
                out[code] = str(raw)
            else:
                problems.append({"field": f"specs.{code}", "code": "bad_choice"})
        elif spec.kind == Kind.number:
            try:
                value = Decimal(str(raw).replace(",", "."))
            except InvalidOperation:
                problems.append({"field": f"specs.{code}", "code": "bad_number"})
                continue
            if value < 0 or value > 1_000_000:
                problems.append({"field": f"specs.{code}", "code": "bad_number"})
                continue
            out[code] = float(value) if value % 1 else int(value)
        else:
            text = " ".join(str(raw).split())[:300]
            if text:
                out[code] = text
    return out, problems
