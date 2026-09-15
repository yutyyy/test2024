#!/usr/bin/env python
# -*- coding: utf-8 -*-

print("Python working correctly!")

# Test import
try:
    from ocr_processor import extract_name_candidate
    print("✓ extract_name_candidate imported successfully")
    
    # Test the function
    test_text = "氏名 水谷   田 大"
    result = extract_name_candidate(test_text)
    print(f"Test result: {repr(result)}")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
