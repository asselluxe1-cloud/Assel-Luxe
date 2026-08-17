import csv
import json
import html
from datetime import datetime, timezone
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, ElementTree, register_namespace

BASE_DIR = Path(__file__).resolve().parent

# =========================
# CONFIG
# =========================

with open(BASE_DIR / "config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

pre_order_days = 1

# =========================
# PRODUCTS
# =========================

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

        if current_price_text:
            current_price = int(float(current_price_text))
        else:
            current_price = 0

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

# =========================
# PRICE RULES
# =========================
#
# ЖАЙ КАРТИНАЛАР:
# 80x160 / 160x80 = қазіргі бағасы
# 100x70 / 70x100 = қазіргі бағасы
# 50x70 / 70x50 = қазіргі бағасы
#
# ПОДСВЕТКА:
# 160x80 / 80x160 = 85000
# 100x70 / 70x100 = 45000
#
# САҒАТ + ПОДСВЕТКА:
# = 59990
#
# ҚАЛҒАН БАРЛЫҚ ӨЛШЕМДЕР:
# қазіргі бағасы өзгермейді.
# =========================

BACKLIGHT_PRICES = {
    "160x80": 85000,
    "80x160": 85000,

    "100x70": 45000,
    "70x100": 45000
}


def get_price(product):

    model = product["model"].lower()
    size = product["size"]

    # Сағат + подсветка
    has_clock = (
        "сағат" in model
        or "час" in model
        or "часы" in model
    )

    has_backlight = (
        "подсвет" in model
        or "подсветка" in model
        or "жарық" in model
    )

    if has_clock and has_backlight:
        return 59990

    # Подсветкасы бар картиналар
    if has_backlight and size in BACKLIGHT_PRICES:
        return BACKLIGHT_PRICES[size]

    # Қалғанының бәрі бұрынғы бағасымен
    return product["current_price"]


# =========================
# XML
# =========================

register_namespace("", "kaspiShopping")

date_string = datetime.now(
    timezone.utc
).strftime("%Y-%m-%dT%H:%M:%SZ")

root = Element(
    "kaspi_catalog",
    {
        "date": date_string,
        "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
        "xsi:schemaLocation": (
            "kaspiShopping "
            "http://kaspi.kz/kaspishopping.xsd"
        )
    }
)

SubElement(root, "company").text = "Assel Luxe"
SubElement(root, "merchantid").text = "Assel-Luxe"

offers = SubElement(root, "offers")

# =========================
# OFFERS
# =========================

for sku, product in products.items():

    price = get_price(product)

    offer = SubElement(
        offers,
        "offer",
        {
            "sku": sku
        }
    )

    SubElement(
        offer,
        "model"
    ).text = html.escape(product["model"])

    SubElement(
        offer,
        "brand"
    ).text = html.escape(product["brand"])

    availabilities = SubElement(
        offer,
        "availabilities"
    )

    for availability in product["availabilities"]:

        stock = availability["stock_count"]
        store_id = availability["store_id"]

        SubElement(
            availabilities,
            "availability",
            {
                "available": "yes",
                "storeId": store_id,
                "preOrder": "1",
                "stockCount": str(stock)
            }
        )

    SubElement(
        offer,
        "price"
    ).text = str(price)


# =========================
# SAVE
# =========================

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
print(f"File: {output}")
print("====================================")
