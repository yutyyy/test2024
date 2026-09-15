import sys
sys.path.insert(0, '.')

from customer_id_app.ocr_processor import extract_name_candidate, extract_text_from_image

# Test 1: Direct function test
test_text = "氏名 水谷   田 大"
result = extract_name_candidate(test_text)
print(f"Test 1 - Direct function: {repr(result)}")

# Test 2: OCR on actual image
try:
    ocr_result = extract_text_from_image("./data/images/images.JPEG")
    full_text = ocr_result.get("text", "")
    name = extract_name_candidate(full_text)
    print(f"Test 2 - OCR on image: {repr(name)}")
    print(f"Full OCR text contains '氏名': {'氏名' in full_text}")
except Exception as e:
    print(f"Test 2 error: {e}")
