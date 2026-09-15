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


def extract_name_from_label_simple(text):
    """シンプル：「氏名」ラベルの直後の最初の2-4漢字を返す"""
    if not text:
        return ""
    
    text_clean = text.replace("\n", " ")
    
    for label in ("氏名", "氏名変更"):
        idx = text_clean.find(label)
        if idx != -1:
            after = text_clean[idx + len(label):].lstrip()
            # 最初の連続漢字2-4文字を抽出
            m = re.match(r"([\u4e00-\u9fa5]{2,4})", after)
            if m:
                return m.group(1)
    
    return ""


# テスト
from ocr_processor import extract_text_from_image
r = extract_text_from_image("./data/images/images.JPEG")
txt = r["text"]
result = extract_name_from_label_simple(txt)
print(f"Simple extraction: {repr(result)}")
