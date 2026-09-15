from pathlib import Path
import re
from ocr_processor import extract_text_from_image

path = Path("./data/images/images.JPEG")
r = extract_text_from_image(str(path))
txt = r["text"]

print("=== FULL OCR TEXT ===")
print(txt)
print("\n=== SEARCHING FOR NAME LABEL ===")
for label in ("氏名変更", "氏名"):
    idx = txt.find(label)
    if idx != -1:
        print(f"\nLabel found: {label} at index {idx}")
        segment = txt[idx:idx+200]
        print(f"Segment: {repr(segment)}")
        
        japanese_tokens = re.findall(r"[\u3041-\u3093\u30a1-\u30f3\u4e00-\u9fa5\u30fb]+", segment)
        print(f"Japanese tokens: {japanese_tokens}")
