from pathlib import Path

from ocr_processor import detect_id_type, extract_id_fields, extract_text_from_image


PROJECT_ROOT = Path(__file__).resolve().parent
IMAGE_DIR = PROJECT_ROOT / "data" / "images"


def validate_image(image_path: str):
    path = Path(image_path)
    if not path.exists():
        print(f"画像が見つかりません: {path}")
        return False

    result = extract_text_from_image(str(path))
    print(f"\n=== {path.name} ===")
    print(f"status: {result['status']}")
    print(f"message: {result['message']}")

    if result["status"] != "ok":
        return False

    print(f"detected_type: {detect_id_type(str(path))}")
    fields = extract_id_fields(str(path), result["text"])
    print(f"name: {fields.get('name', '')}")
    print(f"birth_date: {fields.get('birth_date', '')}")
    print("--- OCR text preview ---")
    text = (result["text"] or "").strip()
    preview = text[:2000]
    print(preview if preview else "(OCR text empty)")
    return True


def main():
    targets = []
    for arg in __import__("sys").argv[1:]:
        targets.append(Path(arg))

    if not targets:
        if IMAGE_DIR.exists():
            targets = sorted(IMAGE_DIR.glob("*"))
        else:
            targets = []

    if not targets:
        print("検証対象の画像がありません。")
        print("使い方:")
        print("  python validate_ocr.py C:/path/to/id_card.jpg")
        print("  または data/images フォルダに JPG を置いて、python validate_ocr.py")
        return 1

    ok_count = 0
    for target in targets:
        if target.is_dir():
            for image in sorted(target.glob("*.jpg")) + sorted(target.glob("*.jpeg")) + sorted(target.glob("*.png")):
                if validate_image(str(image)):
                    ok_count += 1
        else:
            if validate_image(str(target)):
                ok_count += 1

    print(f"\n検証完了: {ok_count} 件の画像を処理しました")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
