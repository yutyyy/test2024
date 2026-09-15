from pathlib import Path
import cv2
from ocr_processor import _read_image_with_fallback, detect_card_contour, warp_card_to_front

path = Path("./data/images/images.JPEG")
img = _read_image_with_fallback(str(path))

if img is None:
    print("Image not found")
else:
    print(f"Original image shape: {img.shape}")
    
    contour = detect_card_contour(img)
    print(f"Contour detected: {contour is not None}")
    if contour is not None:
        print(f"Contour points: {contour}")
    
    warped = warp_card_to_front(img)
    print(f"Warped image shape: {warped.shape}")
    print(f"Warped same as original: {warped is img}")
    
    if warped is not img:
        print("✓ Warp transformation was applied")
    else:
        print("✗ Warp transformation was NOT applied (returned original image)")
