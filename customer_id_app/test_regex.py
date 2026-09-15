import re

txt = "氏名 水谷   田 大"
patterns = [
    (r"氏名\s*([一-龥]{2,8})", "kanji only"),
    (r"氏名\s*([一-龥ぁ-ん]{2,8})", "with hiragana"),
    (r"氏名.*?([一-龥]{2,8})", "lazy match"),
]

for pat, desc in patterns:
    m = re.search(pat, txt)
    print(f"{desc}: {m.group(1) if m else 'NONE'}")

print(f"\nActual target text: {repr(txt)}")
