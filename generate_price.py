import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, ElementTree, register_namespace

BASE_DIR = Path(__file__).resolve().parent

with open(BASE_DIR / "config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

# PreOrder = 1 күн
PRE_ORDER_DAYS = 1

products = {}

with open(
    BASE_DIR / "products.csv",
    "r",
    encoding="utf-8-sig",
    newline=""
) as f:

    reader = csv.DictReader(f)

    required = {
        "sku",
        "model",
        "brand",
        "size",
        "store_id",
        "stock_count",
        "current_price"
    }

    missing = required - set(reader.fieldnames or [])

    if missing:
        raise ValueError(
            "products.csv ішінде бағандар жетіспейді: "
            + ", ".join(sorted(missing))
        )

    for row in reader:

        sku = row["sku"].strip()

        if not sku:
            continue

        size = row["size"].strip().lower().replace(" ", "")

        current_price_text = row["current_price"].strip()

        current_price = (
            int(float(current_price_text))
            if current_price_text
            else 0
        )

        products.setdefault(
            sku,
            {
                "model": row["model"].strip(),
                "brand": row["brand"].strip(),
                "size": size,
                "current_price": current_price,
                "availabilities": []
            }
        )

        products[sku]["availabilities"].append(
            {
                "store_id": row["store_id"].strip(),
                "stock_count": int(
                    float(row["stock_count"] or 0)
                )
            }
        )


# ============================================================
# БАҒА ЕРЕЖЕЛЕРІ
# ============================================================

# Подсветка
BACKLIGHT_PRICES = {
    "160x80": 74990,
    "80x160": 74990,
    "100x70": 44990,
    "70x100": 44990,
    "50x70": 19990,
    "70x50": 19990
}

# Сағатпен
CLOCK_PRICES = {
    "160x80": 59990,
    "80x160": 59990,
    "100x70": 39990,
    "70x100": 39990
}

# Қарапайым картина
ORDINARY_PRICES = {
    "160x80": 49990,
    "80x160": 49990,
    "100x70": 39990,
    "70x100": 39990,
    "50x70": 14000,
    "70x50": 14000
}

# Модуль — ТЕК нақты көрсетілгендері
MODULE_PRICES = {
    "50x70": 74990,
    "70x50": 74990,
    "100x70": 119990,
    "70x100": 119990
}


def has_backlight(model):
    text = model.lower()

    return (
        "подсвет" in text
        or "подсветка" in text
        or "светом" in text
        or "жарық" in text
    )


def has_clock(model):
    text = model.lower()

    return (
        "часы" in text
        or "часами" in text
        or "час " in text
        or "сағат" in text
        or "clock" in text
    )


def is_module(model):
    text = model.lower()

    return (
        "модуль" in text
        or "модульная" in text
        or "модульная картина" in text
    )


def get_price(product):

    model = product["model"]
    size = product["size"]

    # --------------------------------------------------------
    # 1. МОДУЛЬ
    # --------------------------------------------------------
    #
    # 50x70 модуль = 74 990
    # 100x70 модуль = 119 990
    #
    # 80x80 және басқа модульдерге ТИМЕЙМІЗ.
    # --------------------------------------------------------

    if is_module(model):

        if size in MODULE_PRICES:
            return MODULE_PRICES[size]

        return product["current_price"]


    # --------------------------------------------------------
    # 2. САҒАТ + ПОДСВЕТКА / САҒАТТЫ КАРТИНА
    # --------------------------------------------------------

    if has_clock(model):

        if size in CLOCK_PRICES:
            return CLOCK_PRICES[size]

        return product["current_price"]


    # --------------------------------------------------------
    # 3. ПОДСВЕТКА
    # --------------------------------------------------------

    if has_backlight(model):

        if size in BACKLIGHT_PRICES:
            return BACKLIGHT_PRICES[size]

        # Басқа өлшемдердің бағасын өзгертпейміз
        return product["current_price"]


    # --------------------------------------------------------
    # 4. ҚАРАПАЙЫМ КАРТИНА
    # --------------------------------------------------------

    if size in ORDINARY_PRICES:
        return ORDINARY_PRICES[size]


    # --------------------------------------------------------
    # 5. ҚАЛҒАНЫНЫҢ БӘРІ
    # --------------------------------------------------------
    #
    # Стандарт емес өлшемдер
    # Басқа стандарт өлшемдер
    # Басқа модульдер
    # Басқа подсветкалар
    #
    # БАРЛЫҒЫНЫҢ БҰРЫНҒЫ БАҒАСЫ САҚТАЛАДЫ.
    # --------------------------------------------------------

    return product["current_price"]


# ============================================================
# KASPI XML
# ============================================================

register_namespace("", "kaspiShopping")

date_string = datetime.now(
    timezone.utc
).strftime("%Y-%m-%dT%H:%M:%SZ")


root = Element(
    "{kaspiShopping}kaspi_catalog",
    {
        "date": date_string,
        "{http://www.w3.org/2001/XMLSchema-instance}schemaLocation":
            "kaspiShopping http://kaspi.kz/kaspishopping.xsd"
    }
)


SubElement(
    root,
    "{kaspiShopping}company"
).text = "Assel Luxe"


SubElement(
    root,
    "{kaspiShopping}merchantid"
).text = "Assel-Luxe"


offers = SubElement(
    root,
    "{kaspiShopping}offers"
)


# ============================================================
# ТАУАРЛАР
# ============================================================

for sku, product in products.items():

    price = get_price(product)

    offer = SubElement(
        offers,
        "{kaspiShopping}offer",
        {
            "sku": sku
        }
    )

    SubElement(
        offer,
        "{kaspiShopping}model"
    ).text = product["model"]


    SubElement(
        offer,
        "{kaspiShopping}brand"
    ).text = product["brand"]


    availabilities = SubElement(
        offer,
        "{kaspiShopping}availabilities"
    )


    for availability in product["availabilities"]:

        SubElement(
            availabilities,
            "{kaspiShopping}availability",
            {
                "available": "yes",
                "storeId": availability["store_id"],
                "preOrder": str(PRE_ORDER_DAYS),
                "stockCount": str(
                    availability["stock_count"]
                )
            }
        )


    SubElement(
        offer,
        "{kaspiShopping}price"
    ).text = str(price)


# ============================================================
# ФАЙЛДЫ САҚТАУ
# ============================================================

output = BASE_DIR / "kaspi.xml"

tree = ElementTree(root)

tree.write(
    output,
    encoding="utf-8",
    xml_declaration=True
)


print("====================================")
print("Kaspi XML generated successfully")
print(f"Products: {len(products)}")
print("PreOrder: 1 day")
print("Price rules applied")
print(f"File: {output}")
print("====================================")
