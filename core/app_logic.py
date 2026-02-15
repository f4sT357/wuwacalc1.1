"""
Application Logic Module (PySide6)

Provides core application logic including OCR, data loading/saving, and character profile management.
"""

import os
import re
import shutil
import time
from typing import Optional, Any, Callable, Tuple, Dict
from core.data_contracts import OCRResult
from core.ocr_parser import OcrParser
from pytesseract import Output

from PySide6.QtCore import QObject, Signal
from utils.constants import (
    OCR_ENGINE_PILLOW,
)

try:
    from PIL import Image, ImageOps, ImageEnhance, ImageQt

    is_pil_installed = True
except ImportError:
    is_pil_installed = False

try:
    import pytesseract

    is_pytesseract_installed = True
except ImportError:
    is_pytesseract_installed = False


class AppLogic(QObject):
    log_message = Signal(str)
    ocr_error = Signal(str, str)
    info_message = Signal(str, str)

    def __init__(self, tr_func: Callable, data_manager: Any, config_manager: Any) -> None:
        super().__init__()
        self.tr = tr_func
        self.data_manager = data_manager
        self.config_manager = config_manager
        self.ocr_parser = OcrParser(data_manager, tr_func)
        self._setup_tesseract_path()

    def _setup_tesseract_path(self) -> None:
        """Resolves and sets the Tesseract executable path once."""
        if not is_pytesseract_installed:
            return

        if not getattr(pytesseract.pytesseract, "tesseract_cmd", None) or not os.path.isfile(
            str(pytesseract.pytesseract.tesseract_cmd)
        ):
            found = shutil.which("tesseract")
            if found:
                pytesseract.pytesseract.tesseract_cmd = found
                self.log_message.emit(self.tr("tesseract_found_path", found))
            else:
                self.log_message.emit(self.tr("tesseract_not_found_sys"))

    def _perform_ocr(self, image: "Image.Image", language: str = "ja") -> Optional[str]:
        start_time = time.time()
        if not is_pytesseract_installed:
            self.log_message.emit(self.tr("pytesseract_not_installed"))
            return None
        
        if not pytesseract.pytesseract.tesseract_cmd:
            self._setup_tesseract_path()
            if not pytesseract.pytesseract.tesseract_cmd:
                return None

        try:
            processed = self._preprocess_for_ocr(image)
            self.log_message.emit(f"Image for Tesseract OCR - size: {processed.size}, mode: {processed.mode}")
            custom_config = "--oem 3 --psm 6"  # に戻す

            # Use appropriate Tesseract language data
            if language == "zh-CN":
                tess_lang = "chi_sim+eng"
            else:
                tess_lang = "jpn+eng"

            # Tesseractの出力を生バイト列として取得
            output_bytes = pytesseract.image_to_string(
                processed, lang=tess_lang, config=custom_config, output_type=Output.BYTES
            )

            # 生バイト列をUTF-8でデコード。デコードエラーは無視する。
            ocr_text = output_bytes.decode("utf-8", errors="ignore")

            # クリーンアップ: 記号や不要な空白を除去してマッピング精度を上げる
            ocr_text = re.sub(r'[|｜・°º«»〝〟"\'‘] ', "", ocr_text)

            end_time = time.time()
            self.log_message.emit(f"OCR process took {end_time - start_time:.2f} seconds. Language: {tess_lang}")
            self.log_message.emit(f"OCR Raw Text:\n{ocr_text.strip()}")  # ここで生テキストを出力
            return ocr_text
        except pytesseract.TesseractError as te:
            self.ocr_error.emit(self.tr("ocr_error_title"), self.tr("ocr_lang_data_error", te))
            self.log_message.emit(self.tr("ocr_lang_data_error_log", te))
        except FileNotFoundError as fnf:
            self.ocr_error.emit(self.tr("ocr_error_title"), self.tr("tesseract_exec_not_found", fnf))
            self.log_message.emit(self.tr("tesseract_exec_error_log", fnf))
        except Exception as ocr_error:
            self.ocr_error.emit(self.tr("ocr_error_title"), self.tr("ocr_process_error", ocr_error))
            self.log_message.emit(self.tr("ocr_process_error_log", ocr_error))
        return None

    def _parse_ocr_text(self, ocr_text: str) -> OCRResult:
        """
        Parses raw OCR text into a structured OCRResult.
        """
        app_config = self.config_manager.get_app_config()
        return self.ocr_parser.parse(ocr_text, app_config.language)

    def _preprocess_for_ocr(self, image: "Image.Image") -> "Image.Image":
        if not is_pil_installed or image is None:
            return image

        # Determine which engine to use
        engine = self.config_manager.get_app_config().ocr_engine
        # --- Default Pillow-based preprocessing ---
        self.log_message.emit("Using standard Pillow image preprocessing.")
        processed = image.convert("L")
        max_side = max(processed.size)
        if max_side < 1600:
            scale = 2
            processed = processed.resize((processed.width * scale, processed.height * scale), Image.Resampling.LANCZOS)
        processed = ImageOps.autocontrast(processed)
        processed = ImageEnhance.Contrast(processed).enhance(2.0)
        processed = ImageEnhance.Sharpness(processed).enhance(1.5)
        threshold = 150
        processed = processed.point(lambda p: 255 if p > threshold else 0)
        return processed

    def _perform_ocr_with_boxes(self, image: "Image.Image", language: str = "ja") -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        start_time = time.time()
        if not is_pytesseract_installed:
            self.log_message.emit(self.tr("pytesseract_not_installed"))
            return None, None
        
        if not pytesseract.pytesseract.tesseract_cmd:
            self._setup_tesseract_path()
            if not pytesseract.pytesseract.tesseract_cmd:
                return None, None

        try:
            processed = self._preprocess_for_ocr(image)
            self.log_message.emit(f"Image for Tesseract OCR (Boxes) - size: {processed.size}, mode: {processed.mode}")
            custom_config = "--oem 3 --psm 6"

            if language == "zh-CN":
                tess_lang = "chi_sim+eng"
            else:
                tess_lang = "jpn+eng"

            # 1. Get raw text
            output_bytes = pytesseract.image_to_string(
                processed, lang=tess_lang, config=custom_config, output_type=Output.BYTES
            )
            ocr_text = output_bytes.decode("utf-8", errors="ignore")
            ocr_text = re.sub(r'[|｜・°º«»〝〟"\'‘] ', "", ocr_text)

            # 2. Get box data
            # Note: image_to_data might produce slightly different tokenization than image_to_string,
            # but usually it's consistent enough for mapping.
            data = pytesseract.image_to_data(
                processed, lang=tess_lang, config=custom_config, output_type=Output.DICT
            )

            end_time = time.time()
            self.log_message.emit(f"OCR process (with boxes) took {end_time - start_time:.2f} seconds.")
            self.log_message.emit(f"OCR Raw Text:\n{ocr_text.strip()}")
            return ocr_text, data

        except pytesseract.TesseractError as te:
            self.ocr_error.emit(self.tr("ocr_error_title"), self.tr("ocr_lang_data_error", te))
            self.log_message.emit(self.tr("ocr_lang_data_error_log", te))
        except FileNotFoundError as fnf:
            self.ocr_error.emit(self.tr("ocr_error_title"), self.tr("tesseract_exec_not_found", fnf))
            self.log_message.emit(self.tr("tesseract_exec_error_log", fnf))
        except Exception as ocr_error:
            self.ocr_error.emit(self.tr("ocr_error_title"), self.tr("ocr_process_error", ocr_error))
            self.log_message.emit(self.tr("ocr_process_error_log", ocr_error))
        
        return None, None

    def perform_ocr_workflow(self, image: "Image.Image", language: str) -> OCRResult:
        """
        Performs the full OCR workflow including bounding boxes.
        """
        raw_text, data = self._perform_ocr_with_boxes(image, language)
        if raw_text and data:
            return self.ocr_parser.parse_with_boxes(raw_text, data, language)
        return self.ocr_parser.parse(raw_text or "", language)
