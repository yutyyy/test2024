import os
import re
from pathlib import Path

try:
    import cv2
    import numpy as np
    import pytesseract
except Exception:
    cv2 = None
    np = None
    pytesseract = None

try:
    from PIL import Image as PILImage
except Exception:
    PILImage = None


TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
if pytesseract is not None and Path(TESSERACT_PATH).exists():
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
    os.environ["PATH"] = str(Path(TESSERACT_PATH).parent) + os.pathsep + os.environ.get("PATH", "")

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


ERA_START_YEAR = {
    "明治": 1868,
    "大正": 1912,
    "昭和": 1926,
    "平成": 1989,
    "令和": 2019,
}


ID_TEMPLATE_ROIS = {
    "driver_license": {
        "name": (0.20, 0.22, 0.80, 0.38),
        "birth": (0.12, 0.48, 0.82, 0.72),
    },
    "my_number": {
        "name": (0.15, 0.22, 0.75, 0.35),
        "birth": (0.25, 0.39, 0.80, 0.55),
    },
    "residence_card": {
        "name": (0.18, 0.20, 0.80, 0.35),
        "birth": (0.18, 0.42, 0.82, 0.60),
    },
    "passport": {
        "name": (0.20, 0.22, 0.82, 0.38),
        "birth": (0.15, 0.50, 0.82, 0.66),
    },
}


def get_image_size(image_path):
    if not Path(image_path).exists():
        return None

    img = _read_image_with_fallback(image_path)
    if img is None:
        return None

    try:
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


def convert_japanese_era_to_ad(date_text):
    if not date_text:
        return ""

    text = date_text.strip()
    if not text:
        return ""

    m = re.search(r"(明治|大正|昭和|平成|令和)\s*(元|\d{1,3})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日", text)
    if not m:
        return ""

    era_name, year_part, month_part, day_part = m.groups()
    if year_part == "元":
        year = 1
    else:
        year = int(year_part)

    era_start = ERA_START_YEAR.get(era_name, 0)
    gregorian_year = era_start + year - 1

    if era_name == "令和" and year == 1:
        gregorian_year = 2019
    elif era_name == "平成" and year == 1:
        gregorian_year = 1989
    elif era_name == "昭和" and year == 1:
        gregorian_year = 1926
    elif era_name == "大正" and year == 1:
        gregorian_year = 1912
    elif era_name == "明治" and year == 1:
        gregorian_year = 1868

    return f"{gregorian_year}-{int(month_part):02d}-{int(day_part):02d}"


def normalize_date_value(value):
    if not value:
        return ""

    stripped = value.strip()
    if not stripped:
        return ""

    converted = convert_japanese_era_to_ad(stripped)
    if converted:
        return converted

    value = stripped.replace("年", "-").replace("月", "-").replace("日", "")
    value = value.replace("/", "-")
    value = value.replace(".", "-")
    value = re.sub(r"\s+", "", value)
    return value


def extract_name_candidate(text):
    if not text:
        return ""

    normalized = text.replace("\n", " ")

    for label in ("氏名", "氏名変更"):
        idx = normalized.find(label)
        if idx != -1:
            after = normalized[idx + len(label):].lstrip()
            # 複数の漢字グループをスペースを越えて集める（最大8文字）
            # パターン：漢字群 + 任意のスペース + 漢字群の繰り返し
            m = re.match(r"([\u4e00-\u9fa5]+(?:\s+[\u4e00-\u9fa5]+)?)", after)
            if m:
                candidate = m.group(1).replace(" ", "")
                if len(candidate) >= 2 and len(candidate) <= 8:
                    if not _reject_address_like_name(candidate):
                        return candidate
    
    return ""


def extract_birth_candidate(text):
    patterns = [
        r"(明治|大正|昭和|平成|令和)\s*(元|\d{1,3})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日",
        r"生年月日[:：]?\s*(19|20)\d{2}[-/年.]?(0[1-9]|1[0-2])[-/月.]?(0[1-9]|[12]\d|3[01])",
        r"Date of birth[:：]?\s*(19|20)\d{2}[-/](0[1-9]|1[0-2])[-/](0[1-9]|[12]\d|3[01])",
        r"(19|20)\d{2}[-/年.]?(0[1-9]|1[0-2])[-/月.]?(0[1-9]|[12]\d|3[01])",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            raw = match.group(0)
            normalized = normalize_date_value(raw)
            if normalized:
                return normalized
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

    img = _read_image_with_fallback(image_path)
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

    img = _read_image_with_fallback(image_path)
    if img is None:
        return ""

    card_img = warp_card_to_front(img)
    return _ocr_region_on_image(card_img, x_ratio0, y_ratio0, x_ratio1, y_ratio1, psm=psm)


def _distance(a, b):
    return int(np.linalg.norm(np.array(a) - np.array(b))) if np is not None else 0


def detect_card_contour(image):
    if cv2 is None or image is None:
        return None

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(gray, 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    largest = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(largest)
    if area < 5000:
        return None

    peri = cv2.arcLength(largest, True)
    approx = cv2.approxPolyDP(largest, 0.02 * peri, True)
    if len(approx) == 4:
        return approx.reshape(4, 2)

    x, y, w, h = cv2.boundingRect(largest)
    return np.array([[x, y], [x + w, y], [x + w, y + h], [x, y + h]], dtype=np.float32)


def warp_card_to_front(image):
    if cv2 is None or image is None:
        return image

    contour = detect_card_contour(image)
    if contour is None:
        return image

    rect = contour.astype("float32")
    (tl, tr, br, bl) = rect
    width_a = _distance(br, bl)
    width_b = _distance(tr, tl)
    height_a = _distance(tr, br)
    height_b = _distance(tl, bl)
    max_width = max(int(width_a), int(width_b))
    max_height = max(int(height_a), int(height_b))

    if max_width <= 0 or max_height <= 0:
        return image

    dst = np.array([
        [0, 0],
        [max_width - 1, 0],
        [max_width - 1, max_height - 1],
        [0, max_height - 1],
    ], dtype="float32")

    matrix = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(image, matrix, (max_width, max_height))
    return warped


def _ocr_region_on_image(img, x_ratio0, y_ratio0, x_ratio1, y_ratio1, psm=7):
    if cv2 is None or pytesseract is None or img is None:
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
    gray = cv2.resize(gray, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)
    
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)
    
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    
    _, threshold = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 1))
    threshold = cv2.morphologyEx(threshold, cv2.MORPH_CLOSE, kernel, iterations=1)
    
    config = f"--psm {psm}"
    return pytesseract.image_to_string(threshold, lang="jpn+eng", config=config)


def extract_name_and_birth_fields(image_path, text=""):
    if not text:
        if not Path(image_path).exists():
            return {"name": "", "birth_date": ""}
        result = extract_text_from_image(image_path)
        text = result.get("text", "") if result.get("status") == "ok" else ""

    id_type = detect_id_type_from_text(text) if text else detect_id_type(image_path)
    template_fields = extract_fields_by_template_roi(image_path, id_type, text)
    name = template_fields.get("name", "")
    birth_date = template_fields.get("birth_date", "")

    if not name:
        name = extract_name_candidate(text)
    if not name:
        name = extract_name_candidate(ocr_region(image_path, 0.20, 0.18, 0.80, 0.40, psm=7))
    if not name:
        name = extract_name_candidate(ocr_region(image_path, 0.10, 0.12, 0.85, 0.35, psm=6))

    if not birth_date:
        birth_date = extract_birth_candidate(text)
    if not birth_date:
        birth_date = extract_birth_candidate(ocr_region(image_path, 0.15, 0.42, 0.90, 0.70, psm=7))
    if not birth_date:
        birth_date = extract_birth_candidate(ocr_region(image_path, 0.20, 0.40, 0.90, 0.80, psm=6))

    return {
        "name": name,
        "birth_date": birth_date,
    }


def extract_my_number_template_fields(image_path, text=""):
    if not Path(image_path).exists():
        return {"name": "", "birth_date": ""}

    fields = extract_name_and_birth_fields(image_path, text)
    return {
        "name": fields.get("name", ""),
        "birth_date": fields.get("birth_date", ""),
        "personal_number": "",
    }


def extract_id_fields(image_path, text=""):
    if not text:
        if not Path(image_path).exists():
            return {
                "id_type": "unknown",
                "name": "",
                "birth_date": "",
            }
        result = extract_text_from_image(image_path)
        text = result.get("text", "") if result.get("status") == "ok" else ""

    id_type = detect_id_type_from_text(text) if text else detect_id_type(image_path)
    name_and_birth = extract_name_and_birth_fields(image_path, text)

    return {
        "id_type": id_type,
        "name": name_and_birth.get("name", ""),
        "birth_date": name_and_birth.get("birth_date", ""),
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
        img = _read_image_with_fallback(image_path)
        if img is None:
            return {
                "status": "error",
                "message": "画像を読み込めませんでした。",
                "text": "",
            }

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        resized = cv2.resize(gray, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)
        
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        resized = clahe.apply(resized)
        
        resized = cv2.GaussianBlur(resized, (3, 3), 0)
        
        _, threshold = cv2.threshold(resized, 150, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 1))
        threshold = cv2.morphologyEx(threshold, cv2.MORPH_CLOSE, kernel, iterations=1)
        
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


def _read_image_with_fallback(image_path):
    if cv2 is None:
        return None

    img = cv2.imread(str(image_path))
    if img is not None:
        return img

    if PILImage is None or np is None:
        return None

    try:
        pil_image = PILImage.open(str(image_path))
        rgb = pil_image.convert("RGB")
        array = np.asarray(rgb)
        return cv2.cvtColor(array, cv2.COLOR_RGB2BGR)
    except Exception:
        return None


def parse_name_and_birth_date(text):
    normalized = (text or "").replace("\n", " ")
    name = extract_name_candidate(normalized)
    birth_date = extract_birth_candidate(normalized)
    return {
        "name": name,
        "birth_date": birth_date,
    }


def _reject_address_like_name(value):
    if not value:
        return True

    text = value.strip()
    if not text:
        return True
    if "住所" in text or "氏名" in text or "生年月日" in text:
        return True
    if re.search(r"[都道府県市区町村]", text):
        return True
    if re.search(r"(丁目|番地|号|地|線|号室|館|棟|階|ビル|マンション|アパート|建物)", text):
        return True
    return False


def _extract_best_name_from_texts(*candidate_texts):
    values = []
    for candidate_text in candidate_texts:
        if not candidate_text:
            continue
        parsed = extract_name_candidate(candidate_text)
        if parsed and not _reject_address_like_name(parsed):
            values.append(parsed)

    if not values:
        return ""

    kanji_values = [value for value in values if re.search(r"[一-龥]", value)]
    if kanji_values:
        return min(kanji_values, key=lambda value: (len(value), value))

    return min(values, key=lambda value: (len(value), value))


def _extract_best_birth_from_texts(*candidate_texts):
    values = []
    for candidate_text in candidate_texts:
        if not candidate_text:
            continue
        parsed = extract_birth_candidate(candidate_text)
        if parsed:
            values.append(parsed)

    if not values:
        return ""

    return values[0]


def extract_fields_by_template_roi(image_path, id_type, text=""):
    if not Path(image_path).exists():
        return {"name": "", "birth_date": ""}

    rois = ID_TEMPLATE_ROIS.get(id_type, ID_TEMPLATE_ROIS["my_number"])
    candidate_texts = []

    if text:
        candidate_texts.append(text)

    for key in ("name", "birth"):
        roi = rois.get(key)
        if roi:
            candidate_texts.append(ocr_region(image_path, *roi, psm=7 if key == "name" else 6))
            candidate_texts.append(ocr_region(image_path, *roi, psm=11 if key == "name" else 13))

    name = _extract_best_name_from_texts(*candidate_texts)
    birth_date = _extract_best_birth_from_texts(*candidate_texts)

    if not name:
        name = extract_name_candidate(text or "")
    if not birth_date:
        birth_date = extract_birth_candidate(text or "")

    return {
        "name": name,
        "birth_date": birth_date,
    }
