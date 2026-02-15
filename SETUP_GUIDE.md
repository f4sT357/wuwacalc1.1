# Wuwacalc Setup Guide / 鳴潮音骸計算機 セットアップガイド

ご指定のリポジトリを `C:\Users\itsuk\.gemini\antigravity\scratch\wuwacalc` にセットアップしました。

## すでに完了した作業
1. ソースコードのダウンロードと展開
2. 仮想環境 (`.venv`) の作成
3. Python 依存ライブラリ (`PySide6`, `Pillow`, `pytesseract` など) のインストール
4. 起動用バッチファイル (`run_wuwacalc.bat`) の作成

## あなたが行う必要がある作業
OCR機能（画像の自動読み取り）を使用するには、**Tesseract OCR** のインストールが必要です。

1. **Tesseract OCR のダウンロード**
   - [UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/wiki) から Windows 用インストーラをダウンロードしてください。
2. **インストール**
   - インストール中、「Additional language data」で **Japanese** を選択してください。
   - インストール先はデフォルトの `C:\Program Files\Tesseract-OCR` を推奨します。
3. **アプリの起動**
   - `C:\Users\itsuk\.gemini\antigravity\scratch\wuwacalc\run_wuwacalc.bat` をダブルクリックして実行してください。

---

## Workspace recommendation
このディレクトリを作業スペースとして設定することをお勧めします。
`C:\Users\itsuk\.gemini\antigravity\scratch\wuwacalc`
