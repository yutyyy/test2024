# 顧客管理デスクトップアプリ（CSV版）

このプロジェクトは、身分証の画像を取り込み、名前と生年月日を確認し、既存顧客かどうかを判定する簡易的なデスクトップアプリです。

主な機能:
- 顧客名と生年月日の手入力
- 画像ファイル（JPG）の選択
- 顧客の初回来店/再来店判定
- CSV への保存
- 最終来店日と初回来店日管理

## 前提
- Python 3.10 以上
- Tesseract OCR を別途インストールする必要があります
  - Windows: https://github.com/UB-Mannheim/tesseract/wiki
  - インストール後、`tesseract` コマンドが PATH に入っていることを確認してください

## セットアップ

1. 仮想環境を作成
   python -m venv .venv

2. 依存パッケージをインストール
   .venv\Scripts\activate
   pip install -r requirements.txt

3. アプリを起動
   python app.py

## データ構成

- data/csv/customers.csv: 顧客一覧
- data/csv/visits.csv: 来店履歴
- data/images/: JPG 画像保存先

## 今後の拡張候補
- 身分証のテンプレート判定
- OCR の精度向上
- SQLite への移行
- 顧客一覧表の編集機能
- 手動レビュー機能
