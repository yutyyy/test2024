import csv
from datetime import datetime
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"
CSV_DIR = DATA_DIR / "csv"
IMAGE_DIR = DATA_DIR / "images"
CUSTOMERS_PATH = CSV_DIR / "customers.csv"
VISITS_PATH = CSV_DIR / "visits.csv"

CUSTOMER_FIELDS = [
    "customer_id",
    "name",
    "birth_date",
    "id_type",
    "last_visit_date",
    "first_visit_date",
    "status",
    "note",
    "created_at",
    "updated_at",
]

VISIT_FIELDS = [
    "visit_id",
    "customer_id",
    "visit_date",
    "source_image",
    "extracted_name",
    "extracted_birth_date",
    "manual_checked",
    "created_at",
]


def ensure_data_files():
    CSV_DIR.mkdir(parents=True, exist_ok=True)
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)

    if not CUSTOMERS_PATH.exists():
        with CUSTOMERS_PATH.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CUSTOMER_FIELDS)
            writer.writeheader()

    if not VISITS_PATH.exists():
        with VISITS_PATH.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=VISIT_FIELDS)
            writer.writeheader()


def normalize_name(value):
    if value is None:
        return ""
    return "".join(value.lower().split()).replace("　", "")


def normalize_date(value):
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    return text.replace("/", "-").replace(".", "-")


def today_string():
    return datetime.now().strftime("%Y-%m-%d")


def load_customers():
    ensure_data_files()
    rows = []
    with CUSTOMERS_PATH.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row and any((value or "").strip() for value in row.values()):
                rows.append(row)
    return rows


def save_customers(rows):
    ensure_data_files()
    with CUSTOMERS_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CUSTOMER_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def load_visits():
    ensure_data_files()
    rows = []
    with VISITS_PATH.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row and any((value or "").strip() for value in row.values()):
                rows.append(row)
    return rows


def save_visits(rows):
    ensure_data_files()
    with VISITS_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=VISIT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def generate_customer_id():
    rows = load_customers()
    numbers = []
    for row in rows:
        value = (row.get("customer_id") or "").replace("C", "")
        if value.isdigit():
            numbers.append(int(value))
    next_number = max(numbers) + 1 if numbers else 1
    return f"C{next_number:03d}"


def find_customer_by_name_birth(name, birth_date):
    rows = load_customers()
    target_name = normalize_name(name)
    target_birth = normalize_date(birth_date)

    for row in rows:
        candidate_name = normalize_name(row.get("name", ""))
        candidate_birth = normalize_date(row.get("birth_date", ""))
        if candidate_name == target_name and candidate_birth == target_birth:
            return row
    return None


def create_customer(name, birth_date, id_type="manual", note="", image_path=""):
    ensure_data_files()
    customer = find_customer_by_name_birth(name, birth_date)
    if customer:
        return {
            "status": "existing",
            "customer": customer,
            "message": "既存顧客として認識しました。",
        }

    now = today_string()
    customer_id = generate_customer_id()
    new_customer = {
        "customer_id": customer_id,
        "name": name,
        "birth_date": normalize_date(birth_date),
        "id_type": id_type,
        "last_visit_date": now,
        "first_visit_date": now,
        "status": "active",
        "note": note,
        "created_at": now,
        "updated_at": now,
    }

    rows = load_customers()
    rows.append(new_customer)
    save_customers(rows)

    if image_path:
        add_visit_record(
            customer_id=customer_id,
            visit_date=now,
            source_image=image_path,
            extracted_name=name,
            extracted_birth_date=normalize_date(birth_date),
            manual_checked="yes",
        )

    return {
        "status": "new",
        "customer": new_customer,
        "message": "新規顧客として登録しました。",
    }


def add_visit_record(customer_id, visit_date, source_image, extracted_name="", extracted_birth_date="", manual_checked="no"):
    rows = load_visits()
    new_visit = {
        "visit_id": f"V{len(rows) + 1:05d}",
        "customer_id": customer_id,
        "visit_date": normalize_date(visit_date),
        "source_image": source_image,
        "extracted_name": extracted_name,
        "extracted_birth_date": extracted_birth_date,
        "manual_checked": manual_checked,
        "created_at": today_string(),
    }
    rows.append(new_visit)
    save_visits(rows)

    customers = load_customers()
    for customer in customers:
        if customer.get("customer_id") == customer_id:
            customer["last_visit_date"] = normalize_date(visit_date)
            customer["updated_at"] = today_string()
            if not customer.get("first_visit_date"):
                customer["first_visit_date"] = normalize_date(visit_date)
            break
    save_customers(customers)

    return new_visit


def list_customers():
    return load_customers()


def list_visits():
    return load_visits()
