from pathlib import Path
from ocr_processor import extract_text_from_image, extract_name_candidate

r = extract_text_from_image("./data/images/images.JPEG")
txt = r["text"]

print("=== EXTRACT_NAME_CANDIDATE OUTPUT ===")
result = extract_name_candidate(txt)
print(f"Result: {repr(result)}")

print("\n=== OCR TEXT CONTAINS 氏名 ===")
contains = "氏名" in txt
print(f"Contains: {contains}")

idx = txt.find("氏名")
if idx != -1:
    segment = txt[idx:idx+100]
    print(f"Segment: {repr(segment)}")
else:
    print("NOT FOUND")

print("\n=== FULL OCR TEXT ===")
print(txt)
