"""Demo data for local development: `python -m app.seed`.

Compose: `docker compose run --rm api python -m app.seed`.

All companies and people are fictional. Safe to run twice: does nothing if demo users already exist.
Sign in with DEV_LOGIN=true as any of the emails below.
"""

import asyncio
from datetime import date, time

from sqlalchemy import select

from app.core.search import build_search_text
from app.db import get_sessionmaker
from app.models import (
    Address,
    Category,
    ClientLink,
    ClientSource,
    CommissionRule,
    DeliveryZone,
    Invite,
    Locale,
    Membership,
    OfferRule,
    Organization,
    OrgKind,
    PriceTier,
    Product,
    Role,
    RuleScope,
    SellerProfile,
    TaxRegime,
    Unit,
    User,
    VenueType,
    VerificationStatus,
)

CATEGORIES = [
    ("disposables", {"hy": "Միանգամյա սպասք", "ru": "Одноразовая посуда", "en": "Disposables"}, 1000),
    ("cleaning", {"hy": "Մաքրող միջոցներ", "ru": "Бытовая химия", "en": "Cleaning"}, 1000),
    ("grocery", {"hy": "Նպարեղեն", "ru": "Бакалея", "en": "Grocery"}, 500),
    ("dairy", {"hy": "Կաթնամթերք և պանիր", "ru": "Молочка и сыры", "en": "Dairy & cheese"}, 400),
    ("meat", {"hy": "Միս", "ru": "Мясо", "en": "Meat"}, 300),
    ("produce", {"hy": "Բանջարեղեն և կանաչի", "ru": "Овощи и зелень", "en": "Produce & greens"}, 400),
    ("coffee", {"hy": "Սուրճ և թեյ", "ru": "Кофе и чай", "en": "Coffee & tea"}, 700),
    ("bakery", {"hy": "Հաց և լավաշ", "ru": "Хлеб и лаваш", "en": "Bread & lavash"}, 500),
]

DISTRICTS = ["Kentron", "Arabkir", "Ajapnyak", "Davtashen", "Nor Nork"]


def _name(hy: str, ru: str, en: str) -> dict:
    return {"hy": hy, "ru": ru, "en": en}


async def seed() -> None:
    async with get_sessionmaker()() as s:
        if await s.scalar(select(User).where(User.email == "admin@qb.local")):
            print("demo data already present")
            return

        cats = {}
        for i, (slug, name, bp) in enumerate(CATEGORIES):
            cats[slug] = Category(slug=slug, name=name, sort=i, default_commission_bp=bp)
        s.add_all(cats.values())

        # Commission defaults (docs/01 §6): 0% for the seller's own clients, category rate otherwise
        s.add_all(
            [
                CommissionRule(
                    client_source=ClientSource.seller_invited, rate_bp=0, valid_from=date(2026, 1, 1)
                ),
                CommissionRule(
                    client_source=ClientSource.platform,
                    rate_bp=500,
                    first_order_bonus_bp=250,
                    valid_from=date(2026, 1, 1),
                ),
            ]
        )

        admin = User(name="QB Operator", email="admin@qb.local", locale=Locale.ru, is_platform_admin=True)
        s.add(admin)

        # --- sellers ---
        lori = Organization(
            kind=OrgKind.seller,
            legal_name="Lori Cheese House LLC",
            display_name="Լոռի Պանիր",
            tin="00000001",
            tax_regime=TaxRegime.turnover,
        )
        pack = Organization(
            kind=OrgKind.seller,
            legal_name="Yerevan Pack Supply LLC",
            display_name="Yerevan Pack",
            tin="00000002",
            tax_regime=TaxRegime.vat,
        )
        farm = Organization(
            kind=OrgKind.seller,
            legal_name="Green Valley Farm",
            display_name="Green Valley",
            tin="00000003",
            tax_regime=TaxRegime.micro,
        )
        sellers = [lori, pack, farm]
        # Requisites for documents (fictional). Demo sellers are already verified by the operator.
        requisites = {
            lori: ("Lori, Stepanavan, Shahumyan St 5", "Anahit Hovsepyan", "Ameriabank", "1570012345670100"),
            pack: ("Yerevan, Tigran Mets Ave 48", "Arman Sahakyan", "Ardshinbank", "2470098765430100"),
            farm: ("Ararat, Masis, Orchard St 2", "Gor Mkrtchyan", "IDBank", "1180055555550100"),
        }
        for org, (address, director, bank, account) in requisites.items():
            org.legal_address, org.director_name, org.bank_name, org.bank_account = (
                address,
                director,
                bank,
                account,
            )
            org.verification_status = VerificationStatus.verified
            org.registry_source = "demo"
        s.add_all(sellers)
        await s.flush()

        for org, min_order in ((lori, 15_000), (pack, 20_000), (farm, 10_000)):
            s.add(
                SellerProfile(
                    organization_id=org.id,
                    min_order_amd=min_order,
                    cutoff_time=time(16, 0),
                    lead_days=1,
                    delivery_fee_amd=1_000,
                    free_delivery_from_amd=50_000,
                )
            )
            s.add_all(DeliveryZone(seller_id=org.id, district=d) for d in DISTRICTS)

        seller_users = [
            User(name="Anahit (Lori)", email="lori@qb.local", locale=Locale.hy),
            User(name="Arman (Pack)", email="pack@qb.local", locale=Locale.ru),
            User(name="Gor (Farm)", email="farm@qb.local", locale=Locale.hy),
        ]
        s.add_all(seller_users)
        await s.flush()
        for user, org in zip(seller_users, sellers, strict=True):
            s.add(Membership(user_id=user.id, organization_id=org.id, role=Role.owner))

        # --- products ---
        def product(
            seller,
            cat,
            name,
            unit,
            price,
            *,
            min_qty=1,
            step=1,
            offers=False,
            pack_size=None,
            vat=True,
            tiers=(),
        ):
            p = Product(
                seller_id=seller.id,
                category_id=cats[cat].id,
                name=name,
                unit=unit,
                base_price_amd=price,
                min_qty=min_qty,
                qty_step=step,
                allow_offers=offers,
                pack_size=pack_size,
                vat_included=vat,
                vat_rate_bp=2000 if seller.tax_regime == TaxRegime.vat else 0,
                search_text=build_search_text(name),
                tiers=[PriceTier(min_qty=q, price_amd=pr) for q, pr in tiers],
            )
            s.add(p)
            return p

        lori_cheese = product(
            lori,
            "dairy",
            _name("Լոռի պանիր", "Сыр лори", "Lori cheese"),
            Unit.kg,
            3_500,
            offers=True,
            tiers=[(20, 3_350)],
        )
        product(
            lori, "dairy", _name("Չանախ պանիր", "Сыр чанах", "Chanakh cheese"), Unit.kg, 3_200, offers=True
        )
        product(lori, "dairy", _name("Մածուն", "Мацун", "Matsun"), Unit.l, 900, min_qty=5)
        product(lori, "dairy", _name("Թթվասեր 20%", "Сметана 20%", "Sour cream 20%"), Unit.kg, 1_800)

        product(
            pack,
            "disposables",
            _name("Թղթե բաժակ 250 մլ", "Бумажный стакан 250 мл", "Paper cup 250 ml"),
            Unit.pack,
            4_500,
            pack_size="1000 pcs",
            offers=True,
            tiers=[(10, 4_200)],
        )
        product(
            pack,
            "disposables",
            _name("Կափարիչ 80 մմ", "Крышка 80 мм", "Lid 80 mm"),
            Unit.pack,
            3_800,
            pack_size="1000 pcs",
            offers=True,
        )
        product(
            pack,
            "disposables",
            _name("Անձեռոցիկ 24x24", "Салфетки 24x24", "Napkins 24x24"),
            Unit.pack,
            6_000,
            pack_size="20 x 100 pcs",
        )
        product(
            pack,
            "cleaning",
            _name("Սպասք լվանալու միջոց", "Средство для посуды", "Dish soap"),
            Unit.pcs,
            2_900,
            pack_size="5 l",
        )
        product(
            pack,
            "coffee",
            _name("Սուրճ էսպրեսո", "Кофе эспрессо в зёрнах", "Espresso beans"),
            Unit.kg,
            9_800,
            offers=True,
            tiers=[(10, 9_200)],
        )

        product(farm, "produce", _name("Լոլիկ", "Помидоры", "Tomatoes"), Unit.kg, 650, min_qty=5, vat=False)
        product(farm, "produce", _name("Վարունգ", "Огурцы", "Cucumbers"), Unit.kg, 550, min_qty=5, vat=False)
        product(
            farm,
            "produce",
            _name("Ռեհան", "Базилик (рейхан)", "Basil (reyhan)"),
            Unit.kg,
            2_000,
            min_qty=0.5,
            step=0.5,
            vat=False,
        )
        product(
            farm,
            "produce",
            _name("Կանաչի խառը", "Зелень микс", "Mixed greens"),
            Unit.kg,
            1_500,
            min_qty=1,
            step=0.5,
            vat=False,
        )
        await s.flush()

        # Autopilot from docs/02-mvp.md §6.4: list 3 500, floor 3 000, auto-accept from 3 300
        s.add(
            OfferRule(
                seller_id=lori.id,
                scope=RuleScope.product,
                scope_id=lori_cheese.id,
                min_line_amd=20_000,
                floor_price_amd=3_000,
                auto_accept_price_amd=3_300,
                auto_counter=True,
            )
        )
        s.add(
            OfferRule(
                seller_id=pack.id,
                scope=RuleScope.seller,
                min_line_amd=30_000,
                floor_pct_bp=9_000,
                auto_accept_pct_bp=9_500,
                auto_counter=True,
            )
        )

        # --- buyers ---
        arax = Organization(
            kind=OrgKind.buyer,
            legal_name="Arax Cafe LLC",
            display_name="Cafe Arax",
            tin="00000011",
            tax_regime=TaxRegime.turnover,
            venue_type=VenueType.cafe,
        )
        nova = Organization(
            kind=OrgKind.buyer,
            legal_name="Nova Bar LLC",
            display_name="Bar Nova",
            tin="00000012",
            tax_regime=TaxRegime.vat,
            venue_type=VenueType.bar,
        )
        s.add_all([arax, nova])
        arax.legal_address, arax.director_name = "Yerevan, Abovyan St 10", "Lilit Harutyunyan"
        nova.legal_address, nova.director_name = "Yerevan, Komitas Ave 5", "Karen Vardanyan"
        await s.flush()
        s.add_all(
            [
                Address(organization_id=arax.id, label="Main", text="Abovyan St 10", district="Kentron"),
                Address(organization_id=nova.id, label="Main", text="Komitas Ave 5", district="Arabkir"),
            ]
        )
        owner_arax = User(name="Lilit (Arax)", email="arax@qb.local", locale=Locale.hy)
        chef_arax = User(name="Davit (chef, Arax)", email="chef@qb.local", locale=Locale.ru)
        owner_nova = User(name="Karen (Nova)", email="nova@qb.local", locale=Locale.en)
        s.add_all([owner_arax, chef_arax, owner_nova])
        await s.flush()
        s.add_all(
            [
                Membership(user_id=owner_arax.id, organization_id=arax.id, role=Role.owner),
                Membership(
                    user_id=chef_arax.id,
                    organization_id=arax.id,
                    role=Role.buyer_staff,
                    order_limit_amd=50_000,
                    can_negotiate=False,
                ),
                Membership(user_id=owner_nova.id, organization_id=nova.id, role=Role.owner),
            ]
        )

        # Arax came through Lori's invite (0%); Nova found Yerevan Pack in the catalog (platform rate)
        s.add(
            Invite(seller_id=lori.id, code="LORI-ARAX", created_by=seller_users[0].id, used_by_org_id=arax.id)
        )
        s.add_all(
            [
                ClientLink(seller_id=lori.id, buyer_id=arax.id, source=ClientSource.seller_invited),
                ClientLink(seller_id=pack.id, buyer_id=nova.id, source=ClientSource.platform),
            ]
        )
        await s.commit()
        print("demo data created: admin@, lori@, pack@, farm@, arax@, chef@, nova@ (all @qb.local)")


if __name__ == "__main__":
    asyncio.run(seed())
