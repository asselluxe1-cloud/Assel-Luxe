import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, ElementTree, register_namespace


BASE_DIR = Path(__file__).resolve().parent

# ============================================================
# CONFIG
# ============================================================

with open(BASE_DIR / "config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

PRE_ORDER_DAYS = 2

merchant_id = str(config.get("merchantid", ""))
default_store_id = str(config.get("store_id", ""))


# ============================================================
# MANUAL SETTINGS
# ============================================================

# price_overrides.json:
# Егер белгілі бір тауарға бағаны қолмен қойсаң,
# сол баға автоматты түрде өзгермейді.
#
# Мысалы:
# {
#     "123456789": 70000
# }

price_override_file = BASE_DIR / "price_overrides.json"

if price_override_file.exists():
    with open(price_override_file, "r", encoding="utf-8") as f:
        price_overrides = json.load(f)
else:
    price_overrides = {}


# sale_off.json:
# Тек осы файлға SKU енгізілген тауар ғана сатудан шығарылады.
# Автоматты түрде ешқандай тауар сатудан шығарылмайды.
#
# Мысалы:
# [
#     "123456789",
#     "987654321"
# ]

sale_off_file = BASE_DIR / "sale_off.json"

if sale_off_file.exists():
    with open(sale_off_file, "r", encoding="utf-8") as f:
        sale_off = set(str(x).strip() for x in json.load(f))
else:
    sale_off = set()


# ============================================================
# PRODUCTS
# ============================================================

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

        # Тек Assel Luxe
        if row["brand"].strip().lower() != "assel-luxe1":
            continue

        sku = row["sku"].strip()

        if not sku:
            continue

        # Тек мен sale_off.json-ға қолмен қойған тауар шығады.
        # Басқа тауарларға ТИМЕЙМІЗ.
        if sku in sale_off:
            continue

        size = (
            row["size"]
            .strip()
            .lower()
            .replace(" ", "")
        )

        model = row["model"].strip()

        store_id = (
            row["store_id"].strip()
            or default_store_id
        )

        stock_count = int(
            float(row["stock_count"] or 0)
        )

        current_price = 0

        if row["current_price"].strip():
            current_price = int(
                float(row["current_price"])
            )


        # ====================================================
        # MODULE COUNT
        # ====================================================

        module_count = 0

        possible_columns = [
            "Количество модулей",
            "количество модулей",
            "module_count",
            "modules",
            "quantity_modules"
        ]

        for column in possible_columns:

            if column in row:

                value = str(
                    row[column]
                ).strip()

                if value:

                    try:
                        module_count = int(
                            float(value)
                        )
                    except (
                        ValueError,
                        TypeError
                    ):
                        module_count = 0

                    break


        # Егер модуль деп аталған және
        # стандартты 50x70 / 100x70 болса,
        # 3 модуль деп қабылдаймыз.
        if (
            module_count == 0
            and "модуль" in model.lower()
            and size in (
                "50x70",
                "70x50",
                "100x70",
                "70x100"
            )
        ):
            module_count = 3


        products[sku] = {
            "model": model,
            "brand": row["brand"].strip(),
            "size": size,
            "current_price": current_price,
            "module_count": module_count,
            "availabilities": [
                {
                    "store_id": store_id,
                    "stock_count": stock_count
                }
            ]
        }


# ============================================================
# SIZE
# ============================================================

def normalize_size(size):

    size = (
        size
        .lower()
        .replace(" ", "")
    )

    return {
        "80x160": "160x80",
        "70x100": "100x70",
        "70x50": "50x70"
    }.get(size, size)


# ============================================================
# AUTO PRICE
# ============================================================

def calculate_auto_price(product):

    model = product["model"].lower()

    size = normalize_size(
        product["size"]
    )

    current_price = product["current_price"]

    module_count = product.get(
        "module_count",
        0
    )


    # ========================================================
    # МОДУЛЬ КАРТИНАЛАР
    # ========================================================

    if "модуль" in model:

        # 50x70, 3 модуль
        if (
            size == "50x70"
            and module_count == 3
        ):
            return 75000


        # 100x70, 3 модуль
        if (
            size == "100x70"
            and module_count == 3
        ):
            return 75000


        # Басқа модульдерге ТИМЕЙМІЗ
        return current_price


    # ========================================================
    # ПОДСВЕТКА / САҒАТ
    # ========================================================

    has_light = any(
        word in model
        for word in (
            "подсвет",
            "светодиод",
            "жарық",
            "light"
        )
    )

    has_clock = any(
        word in model
        for word in (
            "час",
            "часы",
            "сағат",
            "clock"
        )
    )


    # ========================================================
    # 160x80
    # ========================================================

    if size == "160x80":

        # Подсветка немесе сағат
        if has_light or has_clock:
            return 75000

        # Кейбір бұрынғы позицияларда подсветка
        # атауда жазылмаған болуы мүмкін.
        #
        # Бұрынғы жүйеде 84990 тұрған 160x80
        # позициялар сақтықпен подсветка/сағат ретінде
        # 75000 болып қалады.
        if current_price >= 80000:
            return 75000

        # Жай 160x80
        return 49990


    # ========================================================
    # 100x70
    # ========================================================

    if size == "100x70":

        # Подсветка / сағат
        if has_light or has_clock:
            return 45000

        # Жай
        return 29990


    # ========================================================
    # 50x70
    # ========================================================

    if size == "50x70":

        # Подсветка / сағат
        if has_light or has_clock:
            return 25000

        # Жай
        return 14990


    # ========================================================
    # ҚАЛҒАН ӨЛШЕМДЕР
    # ========================================================

    # ЕШ НӘРСЕ ӨЗГЕРМЕЙДІ
    return current_price


# ============================================================
# FINAL PRICE
# ============================================================

def calculate_price(sku, product):

    # --------------------------------------------------------
    # ЕҢ БІРІНШІ — ҚОЛМЕН ҚОЙЫЛҒАН БАҒА
    # --------------------------------------------------------

    if sku in price_overrides:

        return int(
            price_overrides[sku]
        )


    # --------------------------------------------------------
    # ҚОЛМЕН БАҒА ҚОЙЫЛМАҒАН ТАУАР
    # --------------------------------------------------------

    return calculate_auto_price(product)


# ============================================================
# KASPI XML
# ============================================================

KASPI_NS = "kaspiShopping"

XSI_NS = (
    "http://www.w3.org/2001/"
    "XMLSchema-instance"
)

register_namespace(
    "",
    KASPI_NS
)

register_namespace(
    "xsi",
    XSI_NS
)


def q(tag):

    return (
        f"{{{KASPI_NS}}}{tag}"
    )


date_string = datetime.now(
    timezone.utc
).strftime(
    "%Y-%m-%dT%H:%M:%SZ"
)


root = Element(
    q("kaspi_catalog"),
    {
        "date": date_string,
        f"{{{XSI_NS}}}schemaLocation":
            "kaspiShopping "
            "http://kaspi.kz/"
            "kaspishopping.xsd"
    }
)


SubElement(
    root,
    q("company")
).text = "Assel Luxe"


SubElement(
    root,
    q("merchantid")
).text = merchant_id


offers = SubElement(
    root,
    q("offers")
)


# ============================================================
# OFFERS
# ============================================================

for sku, product in products.items():

    offer = SubElement(
        offers,
        q("offer"),
        {
            "sku": sku
        }
    )


    SubElement(
        offer,
        q("model")
    ).text = product["model"]


    SubElement(
        offer,
        q("brand")
    ).text = product["brand"]


    availabilities = SubElement(
        offer,
        q("availabilities")
    )


    for availability in product[
        "availabilities"
    ]:

        SubElement(
            availabilities,
            q("availability"),
            {
                "available": "yes",

                "storeId":
                    availability[
                        "store_id"
                    ],

                "preOrder":
                    str(
                        PRE_ORDER_DAYS
                    ),

                "stockCount":
                    str(
                        availability[
                            "stock_count"
                        ]
                    )
            }
        )


    price = calculate_price(
        sku,
        product
    )


    SubElement(
        offer,
        q("price")
    ).text = str(price)


# ============================================================
# SAVE XML
# ============================================================

output = (
    BASE_DIR
    / "kaspi.xml"
)


ElementTree(root).write(
    output,
    encoding="utf-8",
    xml_declaration=True
)


# ============================================================
# LOG
# ============================================================

print(
    "========================================"
)

print(
    "KASPI XML ДАЙЫН"
)

print(
    "========================================"
)

print(
    f"Тауар саны: {len(products)}"
)

print(
    f"PreOrder: {PRE_ORDER_DAYS} күн"
)

print(
    f"Қолмен бекітілген баға: "
    f"{len(price_overrides)}"
)

print(
    f"Қолмен сатудан шығарылған: "
    f"{len(sale_off)}"
)

print(
    f"Merchant ID: {merchant_id}"
)

print(
    f"Store ID: {default_store_id}"
)

print(
    f"XML: {output}"
)

print(
    "========================================"
)
