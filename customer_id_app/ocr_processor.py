import re
from pathlib import Path

try:
    import cv2
    import pytesseract
except Exception:
    cv2 = None
    pytesseract = None


ID_TYPE_PATTERNS = {
    "driver_license": [
        "免許証",
        "運転免許",
        "免許",
        "有効期限",
        "生年月日",
    ],
    "my_number": [
        "マイナンバー",
        "個人番号",
        "マイナンバーカード",
        "マイナンバーカード",
        "住民票",
        "住民基本台帳",
    ],
    "residence_card": [
        "在留カード",
        "在留期間",
        "在留資格",
    ],
    "passport": [
        "PASSPORT",
        "passport",
        "Nationality",
        "Date of birth",
    ],
}


def get_image_size(image_path):
    if not Path(image_path).exists():
        return None

    if cv2 is None:
        return None

    try:
        img = cv2.imread(str(image_path))
        if img is None:
            return None
        return img.shape[1], img.shape[0]
    except Exception:
        return None


def detect_id_type_from_text(text):
    normalized = (text or "").replace("\n", " ")
    score = {name: 0 for name in ID_TYPE_PATTERNS}

    for id_type, keywords in ID_TYPE_PATTERNS.items():
        for key in keywords:
            if key in normalized:
                score[id_type] += 1

    # マイナンバーは個人番号の12桁も強く見る
    m = re.search(r"\d{4}[- ]?\d{4}[- ]?\d{4}", normalized)
    if m:
        score["my_number"] += 3

    if not any(score.values()):
        return "unknown"

    candidate = max(score, key=score.get)
    if score[candidate] <= 0:
        return "unknown"
    return candidate


def detect_id_type(image_path):
    if not Path(image_path).exists():
        return "unknown"

    result = extract_text_from_image(image_path)
    if result["status"] != "ok":
        return "unknown"

    text = result["text"]
    detected = detect_id_type_from_text(text)
    if detected != "unknown":
        return detected

    size = get_image_size(image_path)
    if size:
        width, height = size
        ratio = width / max(height, 1)
        if ratio > 1.55:
            return "driver_license"
        if 1.1 <= ratio <= 1.55:
            return "my_number"
    return "unknown"


def normalize_date_value(value):
    if not value:
        return ""
    value = value.strip().replace("年", "-").replace("月", "-").replace("日", "")
    value = value.replace("/", "-")
    value = value.replace(".", "-")
    value = re.sub(r"\s+", "", value)
    return value


def extract_name_candidate(text):
    if not text:
        return ""

    patterns = [
        r"氏名[:：]?\s*([A-Za-zぁ-んァ-ン一-龥・\s]{2,30})",
        r"名前[:：]?\s*([A-Za-zぁ-んァ-ン一-龥・\s]{2,30})",
        r"Name[:：]?\s*([A-Za-z\s]{2,30})",
        r"\b([A-Za-zぁ-んァ-ン一-龥・]{2,30})\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        candidate = match.group(1).strip()
        candidate = candidate.replace("\n", "").replace(" ", "")
        if candidate and len(candidate) >= 2:
            return candidate
    return ""


def extract_birth_candidate(text):
    patterns = [
        r"生年月日[:：]?\s*(19|20)\d{2}[-/年.]?(0[1-9]|1[0-2])[-/月.]?(0[1-9]|[12]\d|3[01])",
        r"Date of birth[:：]?\s*(19|20)\d{2}[-/](0[1-9]|1[0-2])[-/](0[1-9]|[12]\d|3[01])",
        r"(19|20)\d{2}[-/年.]?(0[1-9]|1[0-2])[-/月.]?(0[1-9]|[12]\d|3[01])",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return normalize_date_value(match.group(0))
    return ""


def extract_my_number_candidate(text):
    patterns = [
        r"個人番号[:：]?\s*([0-9\s-]{12,20})",
        r"マイナンバー[:：]?\s*([0-9\s-]{12,20})",
        r"\b(\d{4}[- ]?\d{4}[- ]?\d{4})\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            value = re.sub(r"\D", "", match.group(1))
            if len(value) == 12:
                return value
    return ""


def preprocess_image(image_path):
    if cv2 is None:
        return None

    img = cv2.imread(str(image_path))
    if img is None:
        return None

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    gray = cv2.bilateralFilter(gray, 9, 75, 75)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)
    _, threshold = cv2.threshold(gray, 170, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return threshold


def ocr_region(image_path, x_ratio0, y_ratio0, x_ratio1, y_ratio1, psm=7):
    if cv2 is None or pytesseract is None:
        return ""

    img = cv2.imread(str(image_path))
    if img is None:
        return ""

    h, w = img.shape[:2]
    x0 = max(0, int(w * x_ratio0))
    y0 = max(0, int(h * y_ratio0))
    x1 = min(w, int(w * x_ratio1))
    y1 = min(h, int(h * y_ratio1))
    roi = img[y0:y1, x0:x1]
    if roi.size == 0:
        return ""

    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
    _, threshold = cv2.threshold(gray, 170, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    config = f"--psm {psm}"
    return pytesseract.image_to_string(threshold, lang="jpn+eng", config=config)


def extract_my_number_template_fields(image_path, text=""):
    if not Path(image_path).exists():
        return {"name": "", "birth_date": "", "personal_number": ""}

    if not text:
        result = extract_text_from_image(image_path)
        text = result.get("text", "") if result.get("status") == "ok" else ""

    name = extract_name_candidate(text)
    birth_date = extract_birth_candidate(text)
    personal_number = extract_my_number_candidate(text)

    if not name:
        name = extract_name_candidate(ocr_region(image_path, 0.15, 0.15, 0.85, 0.45, psm=7))
    if not birth_date:
        birth_date = extract_birth_candidate(ocr_region(image_path, 0.15, 0.5, 0.80, 0.75, psm=7))
    if not personal_number:
        personal_number = extract_my_number_candidate(ocr_region(image_path, 0.10, 0.65, 0.95, 0.90, psm=6))

    return {
        "name": name,
        "birth_date": birth_date,
        "personal_number": personal_number,
    }


def extract_id_fields(image_path, text=""):
    if not text:
        if not Path(image_path).exists():
            return {
                "id_type": "unknown",
                "name": "",
                "birth_date": "",
                "personal_number": "",
            }
        result = extract_text_from_image(image_path)
        text = result.get("text", "") if result.get("status") == "ok" else ""

    id_type = detect_id_type_from_text(text) if text else detect_id_type(image_path)
    name = extract_name_candidate(text)
    birth_date = extract_birth_candidate(text)
    personal_number = ""

    if id_type == "my_number":
        template_fields = extract_my_number_template_fields(image_path, text)
        if not name:
            name = template_fields.get("name", "")
        if not birth_date:
            birth_date = template_fields.get("birth_date", "")
        personal_number = template_fields.get("personal_number", "")
    else:
        personal_number = extract_my_number_candidate(text)

    return {
        "id_type": id_type,
        "name": name,
        "birth_date": birth_date,
        "personal_number": personal_number,
    }


def extract_text_from_image(image_path):
    if not Path(image_path).exists():
        return {
            "status": "error",
            "message": "画像が見つかりませんでした。",
            "text": "",
        }

    if cv2 is None or pytesseract is None:
        return {
            "status": "unavailable",
            "message": "OpenCV または Tesseract が未インストールです。",
            "text": "",
        }

    try:
        img = cv2.imread(str(image_path))
        if img is None:
            return {
                "status": "error",
                "message": "画像を読み込めませんでした。",
                "text": "",
            }

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        resized = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        _, threshold = cv2.threshold(resized, 180, 255, cv2.THRESH_BINARY)
        text = pytesseract.image_to_string(threshold, lang="jpn+eng")
        return {
            "status": "ok",
            "message": "OCR の実行が完了しました。",
            "text": text,
        }
    except Exception as exc:
        return {
            "status": "error",
            "message": str(exc),
            "text": "",
        }


def parse_name_and_birth_date(text):
    normalized = (text or "").replace("\n", " ")
    name = extract_name_candidate(normalized)
    birth_date = extract_birth_candidate(normalized)
    return {
        "name": name,
        "birth_date": birth_date,
    }
