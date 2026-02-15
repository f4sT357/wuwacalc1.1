# Wuthering Waves Echo Score Calculator プロセスフロー

本ドキュメントでは、アプリの内部動作、ファイル構成、OCR処理、およびスコア計算のロジックについて詳細に解説します。

---

## 1. 全体アーキテクチャ
アプリは **PySide6** をベースとしたマルチコンポーネント構成となっています。

- **Main Window (`wuwacalc17.py`)**: アプリの起動、各コンポーネントの初期化、イベントの橋渡し。
- **Core Logic**:
    - `AppContext`: 各種マネージャやロジッククラスを保持する依存注入コンテナ。
    - `AppLogic`: OCRの実行（前処理、Tesseract呼び出し）を管理。
    - `ScoreCalculator`: スコア計算エンジンの核心。
    - `ImageProcessor`: クリップボードやファイルからの画像取得、クロップ処理、OCR後のデータルーティング。
- **Managers**:
    - `ConfigManager`: `config.json` の読み書き。
    - `CharacterManager`: キャラクタープロフィール（名前、属性、推奨ステータスの重み）の管理。
    - `TabManager`: 各エボ（タブ）に紐付くデータ（ステータス、画像、計算結果）の管理。
    - `ThemeManager`: UIテーマ（Dark/Light/Clear）の適用。
- **UI Components**:
    - `UIComponents`: ウィジェットの生成とレイアウト構築。
    - `EventHandlers`: UI操作（クリック、選択変更）と内部ロジックの紐付け。
    - `HtmlRenderer`: 計算結果を美しいHTML（CSS組み込み）として描画。

---

## 2. ファイル構成
プロジェクトの主要なファイル構成は以下の通りです。

```text
wuwacalc/
├── wuwacalc17.py          # エントリポイント（メインウィンドウ）
├── core/                  # コアロジック (OCR, 計算エンジン, データ定義)
│   ├── app_logic.py
│   ├── app_setup.py
│   ├── data_contracts.py
│   ├── echo_data.py
│   ├── image_processor.py
│   ├── ocr_parser.py
│   └── score_calculator.py
├── managers/              # 各種管理クラス (設定, データ, キャラ, テーマ, タブ)
│   ├── character_manager.py
│   ├── config_manager.py
│   ├── data_manager.py
│   ├── history_manager.py
│   ├── tab_manager.py
│   ├── theme_manager.py
├── ui/                    # UI関連 (コンポーネント, イベント, ダイアログ)
│   ├── dialogs/           # 各種設定・入力ダイアログ
│   ├── event_handlers.py
│   ├── html_renderer.py
│   ├── ui_components.py
│   └── ui_constants.py
├── utils/                 # ユーティリティ (定数, ロガー, 翻訳, 汎用関数)
│   ├── constants.py
│   ├── languages.py
│   ├── logger.py
│   └── utils.py
├── data/                  # 共通データファイル (JSON)
├── character_settings_jsons/ # 各キャラの個別設定 (JSON)
└── tools/                 # 開発・ビルド補助ツール
```

---

## 3. OCR処理フロー (`Paste` or `Import` → `Parse`)
画像から数値を抽出するまでの一連の流れです。

1.  **画像入力**:
    - `Clipboard` または `File` から画像を取得し、`ImageProcessor` へ渡す。
2.  **前処理 (`AppLogic._preprocess_for_ocr`)**:
    - **Pillow エンジン** を使用。
    - グレースケール化、リサイズ（解像度不足時）、コントラスト調整、2値化を行い、OCR精度を最大化する。
3.  **OCR実行 (`pytesseract`)**:
    - 言語設定 `jpn+eng` を使用。
    - 文字列だけでなく、Bounding Box（文字位置情報）も取得し、後のデータ検証に利用。
4.  **パース (`OcrParser`)**:
    - 正規表現と事前定義されたエイリアスマッピングを用いて、ステータス名と数値を分離。
    - `COST` (1/3/4) の判定、`メインステータス` の特定、5つの `サブステータス` の抽出を行う。
5.  **データ検証・補正**:
    - OCRの読み間違い（例: 点の欠落）を、ゲーム内の理論的な最大値チェックを通じて自動補正。
6.  **自動タブ割り当て (`TabManager.find_best_tab_match`)**:
    - 抽出されたコストやメインステータスを基に、空いているタブ、または既存の適切なタブへデータを自動流し込み。

---

## 4. スコア計算ロジック (`ScoreCalculator`)
現在、以下の5つの指標で評価を行っています：

1.  **正規化スコア (Normalized)**:
    - 各サブステータスの数値を、その項目の最大値（100%）に対する割合で算出。
2.  **期待値比 (Ratio)**:
    - キャラクターごとに設定された「有効ステータス」の期待値を合算。
3.  **ロール評価 (Roll)**:
    - 各項目の最高値を「1.0ロール」とし、合計で何ロール分の強さがあるかを算出（最大 5.0）。
4.  **有効度 (Effective)**:
    - 設定された重み付けに基づき、キャラクターにとってどれだけ無駄のないステータスかを評価。
5.  **Crit Value (CV)**:
    - `会心率 * 2 + 会心ダメージ` の伝統的な評価指標。

---

## 5. データ管理
- **設定ファイル (`config.json`)**: アプリ設定、クロップ位置、最後に選択したキャラなどを保存。
- **キャラクター定義 (`character_settings_jsons/*.json`)**: 各キャラの推奨ステータス、属性、計算用重みを保持。
- **装備履歴 (`equipped_echoes.json`)**: 現在装備中の音骸データを保存し、新しい音骸との比較（スコア増減）を表示可能にする。

---

## 6. 開発履歴と移行
- **PyQt6 → PySide6**: 2025年12月、LGPLライセンスへの準拠とメンテナンス性の向上のため、完全に移行済み。
- **PROCESS_FLOW.md**: 今回、gitignoreから除外され、プロジェクトの公式な技術解説ドキュメントとして再定義された。
