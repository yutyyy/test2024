import os
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from customer_manager import create_customer, find_customer_by_name_birth
from ocr_processor import detect_id_type, extract_id_fields, extract_text_from_image, parse_name_and_birth_date


class CustomerApp(QWidget):
    def __init__(self):
        super().__init__()
        self.image_path = ""
        self.setWindowTitle("顧客管理ツール（CSV版）")
        self.resize(760, 520)

        self.name_edit = QLineEdit()
        self.birth_edit = QLineEdit()
        self.id_type_edit = QLineEdit("manual")
        self.image_edit = QLineEdit()
        self.note_edit = QLineEdit()
        self.result_box = QTextEdit()
        self.result_box.setReadOnly(True)

        self.build_ui()

    def build_ui(self):
        form = QFormLayout()
        form.addRow("氏名", self.name_edit)
        form.addRow("生年月日", self.birth_edit)
        form.addRow("身分証種別", self.id_type_edit)
        form.addRow("メモ", self.note_edit)

        image_row = QHBoxLayout()
        self.image_edit.setPlaceholderText("JPG 画像のパス")
        image_row.addWidget(self.image_edit)
        browse_btn = QPushButton("画像を選択")
        browse_btn.clicked.connect(self.select_image)
        image_row.addWidget(browse_btn)
        form.addRow("画像", image_row)

        check_btn = QPushButton("既存顧客チェック")
        check_btn.clicked.connect(self.check_customer)

        add_btn = QPushButton("顧客登録")
        add_btn.clicked.connect(self.save_customer)

        ocr_btn = QPushButton("OCRで候補抽出")
        ocr_btn.clicked.connect(self.run_ocr)

        buttons = QHBoxLayout()
        buttons.addWidget(check_btn)
        buttons.addWidget(ocr_btn)
        buttons.addWidget(add_btn)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(buttons)
        layout.addWidget(QLabel("結果"))
        layout.addWidget(self.result_box)

    def select_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "画像を選択",
            str(Path.cwd()),
            "JPG画像 (*.jpg *.jpeg)",
        )
        if file_path:
            self.image_path = file_path
            self.image_edit.setText(file_path)

    def check_customer(self):
        name = self.name_edit.text().strip()
        birth = self.birth_edit.text().strip()

        if not name or not birth:
            self.result_box.setPlainText("氏名と生年月日を入力してください。")
            return

        customer = find_customer_by_name_birth(name, birth)
        if customer:
            self.result_box.setPlainText(
                f"既存顧客です。\n"
                f"customer_id: {customer.get('customer_id')}\n"
                f"last_visit_date: {customer.get('last_visit_date')}\n"
                f"first_visit_date: {customer.get('first_visit_date')}"
            )
        else:
            self.result_box.setPlainText("該当する顧客は見つかりませんでした。新規登録として扱えます。")

    def run_ocr(self):
        if not self.image_path:
            self.result_box.setPlainText("画像を選択してください。")
            return

        result = extract_text_from_image(self.image_path)
        if result["status"] != "ok":
            self.result_box.setPlainText(result["message"])
            return

        parsed = parse_name_and_birth_date(result["text"])
        fields = extract_id_fields(self.image_path, result["text"])
        id_type = fields.get("id_type") or detect_id_type(self.image_path)
        self.id_type_edit.setText(id_type)
        personal_number = fields.get("personal_number", "")

        if parsed["name"]:
            self.name_edit.setText(parsed["name"])
        if parsed["birth_date"]:
            self.birth_edit.setText(parsed["birth_date"])

        extra_info = ""
        if personal_number:
            extra_info = f"\n個人番号: {personal_number}"

        self.result_box.setPlainText(
            f"種別判定: {id_type}\n\n"
            f"OCR結果:\n{result['text'][:2000]}\n\n"
            f"候補: name={parsed['name']}, birth_date={parsed['birth_date']}{extra_info}"
        )

    def save_customer(self):
        name = self.name_edit.text().strip()
        birth = self.birth_edit.text().strip()
        id_type = self.id_type_edit.text().strip() or "manual"
        note = self.note_edit.text().strip()

        if not name or not birth:
            self.result_box.setPlainText("氏名と生年月日を入力してください。")
            return

        result = create_customer(name, birth, id_type=id_type, note=note, image_path=self.image_path)
        if result["status"] == "existing":
            self.result_box.setPlainText(
                f"既存顧客でした。\n"
                f"customer_id: {result['customer'].get('customer_id')}\n"
                f"最後の来店日: {result['customer'].get('last_visit_date')}"
            )
        else:
            self.result_box.setPlainText(
                f"{result['message']}\n"
                f"customer_id: {result['customer'].get('customer_id')}\n"
                f"first_visit_date: {result['customer'].get('first_visit_date')}"
            )


if __name__ == "__main__":
    app = QApplication([])
    window = CustomerApp()
    window.show()
    app.exec()
