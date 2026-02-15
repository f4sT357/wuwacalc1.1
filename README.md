# 🌊 鳴潮 音骸スコア計算機 / Wuthering Waves Echo Score Calculator

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-Custom-green.svg)](LICENSE.md)

鳴潮（Wuthering Waves）の音骸（Echo）のスコアを計算・評価するためのデスクトップアプリケーションです。
OCR機能による自動入力、キャラクター別の重み付け設定、多彩な計算方式に対応しています。

A desktop application to calculate and evaluate Echo scores for Wuthering Waves.
Supports automatic input via OCR, character-specific weighting presets, and multiple calculation methods.

---

## 📖 目次 / Table of Contents
- [機能 / Features](#-機能--features)
- [セットアップ / Setup](#-セットアップ--setup)
- [使用方法 / Usage](#-使用方法--usage)
- [計算方式の詳細 / Calculation Methods](#-計算方式の詳細--calculation-methods)
- [免責事項 / Disclaimer](#-免責事項--disclaimer)

---

## ✨ 機能 / Features

### 日本語 (JP)
- **OCR自動入力**: スクリーンショットやクリップボードの画像からステータスを自動認識。
- **インテリジェント配分**: OCR時にコスト(1/3/4)を判別し、適切な空きタブへ自動振り分け。
- **5つの計算方式**: 正規化、比率重視、ロール品質、有効ステータス数、CV換算に対応。
- **キャラクタープリセット**: 各キャラに合わせた有効ステータスと重み付け、参照ステータスを保存可能。
- **装備自動ロード**: キャラクター切り替え時、空いているタブに「装備中」のエコーを自動で読み込みます。
- **5列スコアボード生成**: 現在のビルドを横一列にまとめた画像を生成。スコア評価から「%」を除いた正確な指標を表示。
- **リアルタイム設定反映**: 言語設定や文字色が、再起動なしでUI全体に即座に反映されます。
- **安全なOCR**: 重複防止機能や、クロップ範囲の％指定による精密な読取設定が可能。

### English (EN)
- **OCR Auto-Input**: Automatically recognize stats from screenshots or clipboard images.
- **Intelligent Assignment**: Auto-assigns echoes to tabs based on identified cost (1/3/4).
- **5 Calculation Methods**: Supports Normalization, Ratio, Roll Quality, Effective Stats Count, and Crit Value (CV).
- **Character Presets**: Save effective stats, weighting, and scaling stat (ATK/HP/DEF) for each character.
- **Equipped Auto-Load**: Automatically loads equipped echoes into empty tabs when switching characters.
- **5-Column Scoreboard**: Creates a summary image in a clean single-row layout. Removes misleading "%" from scores.
- **Real-time Updates**: Language and appearance settings are applied instantly to the entire UI.
- **Advanced OCR**: Features duplicate skipping to protect manual edits and conflict detection to prevent accidental overwrites.

---

## 🛠️ セットアップ / Setup

### 1. Python環境の準備
Python 3.8以上が必要です。

```bash
# 仮想環境の作成と有効化 (推奨)
python -m venv .venv
# Windows:
.\.venv\Scripts\Activate.ps1
# Mac/Linux:
source .venv/bin/activate

# 依存関係のインストール
pip install -r requirements.txt
```

### 2. Tesseract OCRのインストール
画像認識のためにTesseractが必要です。
- **Windows**: [UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/wiki) からインストーラをダウンロード。
  - インストール時、`Additional language data` で `Japanese` を選択してください。
  - デフォルトのインストール先 (`C:\Program Files\Tesseract-OCR`) を推奨します。

---

## 🚀 使用方法 / Usage

### 基本操作
1. `wuwacalc17.py` を実行してアプリを起動します。
2. 左上のプルダウンから**キャラクター**を選択します。
3. **音骸のステータスを入力**します。
   - **OCR (自動)**: ゲーム画面の音骸詳細をスクリーンショットし、アプリ上で `Ctrl+V` (貼り付け) を押します。
   - **Manual (手動)**: 直接数値を選択・入力します。
4. 自動的にスコアが計算され、結果が表示されます。

### 便利な機能
*   **装備に設定**: 現在のタブの内容を、そのキャラの装備として保存します。
*   **スコアボード**: 画面左下の「スコアボード」ボタンで、現在のセット全体の画像を生成します。
*   **一括計算 (Batch)**: 5つのタブ全ての合計スコアやバランスを評価します。

---

## 🧮 計算方式の詳細 / Calculation Methods

1. **正規化 (Normalized)**: 各サブステータスを最大値で割り、重み付けして合算します (GameWith風)。
2. **比率重視 (Ratio)**: ステータスの比率とダメージ貢献度を重視します (Keisan風)。
3. **ロール品質 (Roll Quality)**: 数値が最大値に対してどれだけ高いか（跳ねたか）を評価します。
4. **有効ステ数 (Effective Stats)**: 有効なサブステータスの数をカウントし、ボーナスを与えます。
5. **CV換算 (Crit Value)**: 会心率×2 + 会心ダメージ を基準とした、一般的な厳選指標です。

---

## ⚠️ 免責事項 / Disclaimer
本ツールはファンメイドの非公式ツールです。Wuthering Waves（鳴潮）および関連する権利は KURO GAMES に帰属します。
本ツールの使用によって生じたいかなる損害についても、開発者は責任を負いません。
This is an unofficial fan-made tool. Wuthering Waves and related rights belong to KURO GAMES.