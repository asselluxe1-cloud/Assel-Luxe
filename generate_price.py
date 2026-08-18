import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, ElementTree, register_namespace

BASE_DIR = Path(__file__).resolve().parent
with open(BASE_DIR / "config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

pre_order_days = 2
merchant_id = str(config.get("merchantid", ""))
default_store_id = str(config.get("store_id", ""))

description = """✨ Assel Luxe — премиум кристалды картиналар | Премиальные кристальные картины | Premium Crystal Art
💎 **5 қабатты заманауи технология | 5-слойная технология | 5-Layer Technology**
🔹 **Кристалл тастар | Кристальные камни | Crystal Stones** — жарқыраған, сәнді көрініс / роскошный блеск / luxurious shine.
🔹 **Эпоксидті шайыр | Эпоксидная смола | Epoxy Resin** — көлем, тереңдік және жылтыр эффект / объём, глубина и глянец / depth, volume and glossy finish.
🔹 **UV PRINT** — қанық түстер және анық сурет / яркие цвета и чёткое изображение / vivid colors and sharp image.
🔹 **МДФ негіз | Основа из МДФ | MDF Base** — берік және сапалы / прочная и надёжная / durable and reliable.
🔹 **Алтын түсті алюминий жақтау | Золотая алюминиевая рама | Gold Aluminum Frame** — дайын премиум көрініс / завершённый премиальный вид / premium finished look.
🇰🇿 **Қазақстанда жасалады | Произведено в Казахстане | Made in Kazakhstan**
✨ **90% қол еңбегі | 90% ручная работа | 90% Handmade**
🎨 **Жеке тапсырыс | Индивидуальный заказ | Custom Order**
**⏳** Дайындау мерзімі — 1 күн | Срок изготовления — 1 дня | Production time — 1 days
💫 **Assel Luxe — жай ғана картина емес, үйге сән, жарық және ерекше атмосфера сыйлайтын интерьердің премиум бөлігі.**
**Assel Luxe— не просто картина, а стильный премиальный элемент интерьера, создающий красоту и особую атмосферу.**
**Assel Luxe — more than a painting, it is a premium interior element that brings beauty, elegance and a special atmosphere to your home."""

products = {}
with open(BASE_DIR / "products.csv", "r", encoding="utf-8-sig", newline="") as f:
    reader = csv.DictReader(f)
    required = {"sku", "model", "brand", "size", "store_id", "stock_count", "current_price"}
    missing = required - set(reader.fieldnames or [])
    if missing:
        raise ValueError("products.csv ішінде бағандар жетіспейді: " + ", ".join(sorted(missing)))

    for row in reader:
        if row["brand"].strip().lower() != "assel-luxe1":
            continue
        sku = row["sku"].strip()
        if not sku:
            continue
        size = row["size"].strip().lower().replace(" ", "")
        model = row["model"].strip()
        store_id = row["store_id"].strip() or default_store_id
        stock_count = int(float(row["stock_count"] or 0))
        current_price = int(float(row["current_price"])) if row["current_price"].strip() else 0

        module_count = 0
        for column in ("Количество модулей", "количество модулей", "module_count", "modules", "quantity_modules"):
            if column in row and str(row[column]).strip():
                try:
                    module_count = int(float(row[column]))
                except (ValueError, TypeError):
                    module_count = 0
                break
        if module_count == 0 and "модуль" in model.lower() and size in ("50x70", "70x50", "100x70", "70x100"):
            module_count = 3

        products[sku] = {
            "model": model,
            "brand": row["brand"].strip(),
            "size": size,
            "current_price": current_price,
            "module_count": module_count,
            "availabilities": [{"store_id": store_id, "stock_count": stock_count}],
        }


def normalize_size(size):
    return {"80x160": "160x80", "70x100": "100x70", "70x50": "50x70"}.get(size.lower().replace(" ", ""), size.lower().replace(" ", ""))


def calculate_price(product):
    model = product["model"].lower()
    size = normalize_size(product["size"])
    current_price = product["current_price"]
    module_count = product.get("module_count", 0)

    if "модуль" in model:
        if size == "50x70" and module_count == 3:
            return 75000
        if size == "100x70" and module_count == 3:
            return 75000
        return current_price

    has_light = any(word in model for word in ("подсвет", "светодиод", "подсветка"))
    has_clock = any(word in model for word in ("час", "часы", "сағат"))

    # 160/80 немесе 80/160: подсветка/сағат = 75 000.
    # Атауда подсветка жазылмаған арнайы 160/80 позициялар үшін бұрынғы 84 990 баға белгі ретінде алынады.
    hidden_light_160 = size == "160x80" and current_price >= 80000
    if size == "160x80" and (has_light or has_clock or hidden_light_160):
        return 75000

    if size == "100x70" and (has_light or has_clock):
        return 45000
    if size == "50x70" and (has_light or has_clock):
        return 25000

    simple_prices = {"160x80": 49990, "100x70": 39990, "50x70": 14990}
    if size in simple_prices:
        return simple_prices[size]

    return current_price


KASPI_NS = "kaspiShopping"
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"
register_namespace("", KASPI_NS)
register_namespace("xsi", XSI_NS)


def q(tag):
    return f"{{{KASPI_NS}}}{tag}"


date_string = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
root = Element(q("kaspi_catalog"), {
    "date": date_string,
    f"{{{XSI_NS}}}schemaLocation": "kaspiShopping http://kaspi.kz/kaspishopping.xsd",
})
SubElement(root, q("company")).text = "Assel Luxe"
SubElement(root, q("merchantid")).text = merchant_id
offers = SubElement(root, q("offers"))

for sku, product in products.items():
    offer = SubElement(offers, q("offer"), {"sku": sku})
    SubElement(offer, q("model")).text = product["model"]
    SubElement(offer, q("brand")).text = product["brand"]
    availabilities = SubElement(offer, q("availabilities"))
    for availability in product["availabilities"]:
        SubElement(availabilities, q("availability"), {
            "available": "yes",
            "storeId": availability["store_id"],
            "preOrder": str(pre_order_days),
            "stockCount": str(availability["stock_count"]),
        })
    SubElement(offer, q("price")).text = str(calculate_price(product))

output = BASE_DIR / "kaspi.xml"
ElementTree(root).write(output, encoding="utf-8", xml_declaration=True)
print("Kaspi XML дайын.")
print(f"Assel Luxe тауар саны: {len(products)}")
print(f"PreOrder: {pre_order_days} күн")
print(f"Merchant ID: {merchant_id}")
print(f"Store ID: {default_store_id}")
print(f"XML: {output}")
