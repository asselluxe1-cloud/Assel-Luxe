import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, ElementTree, register_namespace

BASE_DIR = Path(__file__).resolve().parent

with open(BASE_DIR / "config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

pre_order_days = int(config.get("pre_order_days", 1))
merchant_id = str(config.get("merchantid", ""))
default_store_id = str(config.get("store_id", ""))

products = {}

with open(BASE_DIR / "products.csv", "r", encoding="utf-8-sig", newline="") as f:
    reader = csv.DictReader(f)

    required = {
        "sku", "model", "brand", "size",
        "store_id", "stock_count", "current_price"
    }

    missing = required - set(reader.fieldnames or [])
    if missing:
        raise ValueError(
            "products.csv ішінде бағандар жетіспейді: "
            + ", ".join(sorted(missing))
        )

    for row in reader:
        # ТЕК ASSEL LUXE
        if row["brand"].strip().lower() != "assel-luxe1":
            continue

        sku = row["sku"].strip()
        if not sku:
            continue

        size = row["size"].strip().lower().replace(" ", "")
        model = row["model"].strip()
        store_id = row["store_id"].strip() or default_store_id
        stock_count = int(float(row["stock_count"] or 0))
        current_price = (
            int(float(row["current_price"]))
            if row["current_price"].strip()
            else 0
        )

        if sku not in products:
            products[sku] = {
                "model": model,
                "brand": row["brand"].strip(),
                "size": size,
                "current_price": current_price,
                "availabilities": []
            }

        products[sku]["availabilities"].append({
            "store_id": store_id,
            "stock_count": stock_count
        })


def normalize_size(size):
    return {
        "80x160": "160x80",
        "70x100": "100x70",
        "70x50": "50x70",
    }.get(size.lower().replace(" ", ""), size.lower().replace(" ", ""))


def calculate_price(product):
    model = product["model"].lower()
    size = normalize_size(product["size"])
    current_price = product["current_price"]

    # Подсветка
    if "подсвет" in model:
        prices = {
            "160x80": 74990,
            "100x70": 44990,
            "50x70": 19990
        }
        if size in prices:
            return prices[size]

    # Сағатпен
    if "час" in model or "часы" in model or "сағат" in model:
        prices = {
            "160x80": 59990,
            "100x70": 39990
        }
        if size in prices:
            return prices[size]

    # Модуль: тек нақты екі өлшем.
    # 80x80 және басқа модульдер бұрынғы бағасында қалады.
    if "модуль" in model:
        prices = {
            "50x70": 74990,
            "100x70": 119990
        }
        return prices.get(size, current_price)

    # Қарапайым картина
    prices = {
        "160x80": 49990,
        "100x70": 39990,
        "50x70": 14000
    }

    return prices.get(size, current_price)


# ------------------------------------------------------------
# ASSEL LUXE DESCRIPTION
# ------------------------------------------------------------

description = """✨ Assel Luxe — премиум кристалды картиналар | Премиальные кристальные картины | Premium Crystal Art

💎 5 қабатты заманауи технология | 5-слойная технология | 5-Layer Technology
🔹 Кристалл тастар | Кристальные камни | Crystal Stones — жарқыраған, сәнді көрініс / роскошный блеск / luxurious shine.
🔹 Эпоксидті шайыр | Эпоксидная смола | Epoxy Resin — көлем, тереңдік және жылтыр эффект / объём, глубина и глянец / depth, volume and glossy finish.
🔹 UV PRINT — қанық түстер және анық сурет / яркие цвета и чёткое изображение / vivid colors and sharp image.
🔹 МДФ негіз | Основа из МДФ | MDF Base — берік және сапалы / прочная и надёжная / durable and reliable.
🔹 Алтын түсті алюминий жақтау | Золотая алюминиевая рама | Gold Aluminum Frame — дайын премиум көрініс / завершённый премиальный вид / premium finished look.

🇰🇿 Қазақстанда жасалады | Произведено в Казахстане | Made in Kazakhstan
✨ 90% қол еңбегі | 90% ручная работа | 90% Handmade
🎨 Жеке тапсырыс | Индивидуальный заказ | Custom Order
⏳ Дайындау мерзімі — 1 күн | Срок изготовления — 1 день | Production time — 1 day

💫 Assel Luxe — жай ғана картина емес, үйге сән, жарық және ерекше атмосфера сыйлайтын интерьердің премиум бөлігі.
Assel Luxe — не просто картина, а стильный премиальный элемент интерьера, создающий красоту и особую атмосферу.
Assel Luxe — more than a painting, it is a premium interior element that brings beauty, elegance and a special atmosphere to your home."""


register_namespace("", "kaspiShopping")

date_string = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

root = Element(
    "kaspi_catalog",
    {
        "date": date_string,
        "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
        "xsi:schemaLocation":
            "kaspiShopping http://kaspi.kz/kaspishopping.xsd"
    }
)

SubElement(root, "company").text = "Assel Luxe"
SubElement(root, "merchantid").text = merchant_id

offers = SubElement(root, "offers")

for sku, product in products.items():

    offer = SubElement(
        offers,
        "offer",
        {"sku": sku}
    )

    SubElement(
        offer,
        "model"
    ).text = product["model"]

    SubElement(
        offer,
        "brand"
    ).text = product["brand"]

    SubElement(
        offer,
        "description"
    ).text = description

    availabilities = SubElement(
        offer,
        "availabilities"
    )

    for availability in product["availabilities"]:

        SubElement(
            availabilities,
            "availability",
            {
                "available": "yes",
                "storeId": availability["store_id"],
                "preOrder": str(pre_order_days),
                "stockCount": str(availability["stock_count"])
            }
        )

    SubElement(
        offer,
        "price"
    ).text = str(calculate_price(product))


output = BASE_DIR / "kaspi.xml"

ElementTree(root).write(
    output,
    encoding="utf-8",
    xml_declaration=True
)

print("Kaspi XML дайын.")
print(f"Assel Luxe тауар саны: {len(products)}")
print(f"PreOrder: {pre_order_days} күн")
print(f"Merchant ID: {merchant_id}")
print(f"Store ID: {default_store_id}")
print(f"XML: {output}")
