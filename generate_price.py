import csv
import json
import html
from datetime import datetime, timezone
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, ElementTree, register_namespace

BASE_DIR = Path(__file__).resolve().parent

with open(BASE_DIR / "config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

pre_order_days = int(config.get("pre_order_days", 1))

prices = config.get("prices", config.get("цены", {}))

products = {}

with open(BASE_DIR / "products.csv", "r", encoding="utf-8-sig", newline="") as f:
    reader = csv.DictReader(f)

    required = {
        "sku",
        "model",
        "brand",
        "size",
        "store_id",
        "stock_count"
    }

    missing = required - set(reader.fieldnames or [])

    if missing:
        raise ValueError(
            f"products.csv ішінде бағандар жетіспейді: {', '.join(sorted(missing))}"
        )

    for row in reader:
        sku = row["sku"].strip()

        if not sku:
            continue

        products.setdefault(sku, {
            "model": row["model"].strip(),
            "brand": row["brand"].strip(),
            "size": row["size"].strip().lower().replace(" ", ""),
            "availabilities": []
        })

        products[sku]["availabilities"].append({
            "store_id": row["store_id"].strip(),
            "stock_count": int(row["stock_count"] or 0)
        })


register_namespace("", "kaspiShopping")

date_string = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

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

for sku, product in products.items():

    size = product["size"]

    if size not in prices:
        raise ValueError(
            f"{sku}: {size} өлшеміне баға config.json ішінде жоқ"
        )

    price = int(prices[size])

    offer = SubElement(
        offers,
        "offer",
        {"sku": sku}
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
                "preOrder": str(pre_order_days),
                "stockCount": str(stock)
            }
        )

    SubElement(
        offer,
        "price"
    ).text = str(price)

output = BASE_DIR / "kaspi.xml"

tree = ElementTree(root)

tree.write(
    output,
    encoding="utf-8",
    xml_declaration=True
)

print(f"Generated: {output}")
print(f"Products: {len(products)}")
print(f"PreOrder: {pre_order_days} day(s)")
