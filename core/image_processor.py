"""
Image Processing and OCR Module (PySide6)

Provides image loading, cropping, OCR processing, and automatic input.
"""

import os
from typing import Any, List, Set

from PySide6.QtCore import QObject, Signal

try:
    from PIL import Image, ImageQt, ImageGrab

    is_pil_installed = True
except ImportError:
    is_pil_installed = False

from utils.utils import crop_image_by_percent
from core.data_contracts import BatchItemResult, CropConfig, OCRResult
from core.worker_thread import OCRWorker


class ImageProcessor(QObject):
    """Class responsible for image processing and OCR."""

    ocr_completed = Signal(object)  # OCRResult
    log_requested = Signal(str)
    error_occurred = Signal(str, str)
    image_updated = Signal(object)  # Image.Image
    calculation_requested = Signal()

    def __init__(self, logic: "AppLogic", config_manager: Any) -> None:
        """
        Initialization

        Args:
            logic: The application logic instance.
            config_manager: The ConfigManager instance.
        """
        super().__init__()
        self.logic = logic
        self.config_manager = config_manager

        # Internal state
        self.loaded_image = None
        self.original_image = None
        self.manual_crop_rect = None  # (left, top, right, bottom) relative 0.0-1.0

        # Batch processing state
        self._batch_assigned_tabs: Set[str] = set()
        self._batch_successful_count = 0

    def set_manual_crop_rect(self, rect: tuple) -> None:
        """Set manual crop area (left, top, right, bottom) as 0.0-1.0 ratios."""
        self.manual_crop_rect = rect
        self.perform_crop()

    def process_images_from_paths(self, file_paths: List[str]) -> None:
        """Process one or multiple image paths."""
        if not is_pil_installed:
            self.error_occurred.emit("Error", "Pillow is not installed. Image operations require Pillow.")
            return

        if not file_paths:
            return

        try:
            if len(file_paths) == 1:
                # Single image
                file_path = file_paths[0]
                if not os.path.isfile(file_path):
                    self.error_occurred.emit("Error", f"File not found:\n{file_path}")
                    return

                image = Image.open(file_path)
                self.process_loaded_image(image, file_path)
            else:
                # Multiple images
                self.process_batch_images(file_paths)

        except Exception as e:
            self.error_occurred.emit("Error", f"Failed to load image(s):\n{e}")
            self.log_requested.emit(f"Image load error: {e}")

    def process_batch_images(self, file_paths: List[str]) -> None:
        """Process multiple images sequentially in a background thread."""
        self.log_requested.emit(f"Starting batch processing of {len(file_paths)} images...")

        app_config = self.config_manager.get_app_config()
        crop_config = CropConfig(
            mode=app_config.crop_mode,
            left_p=app_config.crop_left_percent,
            top_p=app_config.crop_top_percent,
            width_p=app_config.crop_width_percent,
            height_p=app_config.crop_height_percent,
        )

        self._batch_assigned_tabs = set()
        self._batch_successful_count = 0

        self.worker = OCRWorker(self.logic, file_paths, crop_config, app_config.language)
        self.worker.signals.result.connect(self._on_worker_result)
        self.worker.signals.finished.connect(self._on_worker_finished)
        self.worker.signals.error.connect(self._on_worker_error)
        self.worker.signals.progress.connect(self._on_worker_progress)
        self.worker.signals.log.connect(self.log_requested.emit)

        self.worker.start()

    def _on_worker_progress(self, current: int, total: int) -> None:
        self.log_requested.emit(f"Progress: {current}/{total}")

    def _on_worker_error(self, err: tuple) -> None:
        exctype, value, traceback_str = err
        self.log_requested.emit(f"Worker Error: {value}")

    def _on_worker_result(self, data: BatchItemResult) -> None:
        """Handle a single OCR result from the worker."""
        # This signal should be handled by app/tab_manager to assign results to tabs
        # For now, we emit ocr_completed for each result in batch
        self.ocr_completed.emit(data)
        self._batch_successful_count += 1

    def _on_worker_finished(self) -> None:
        self.log_requested.emit(
            f"Batch processing completed. {self._batch_successful_count} images processed successfully."
        )

        if self.config_manager.get_app_config().auto_calculate:
            self.calculation_requested.emit()

    def process_loaded_image(self, image: "Image.Image", file_path: str = None) -> None:
        """Process a single loaded PIL Image."""
        self.original_image = image.convert("RGB")
        self.log_requested.emit(f"Image loaded: {file_path if file_path else 'Memory'}")
        
        # Reset manual crop on new image
        self.manual_crop_rect = None

        self.perform_crop()

    def paste_from_clipboard(self) -> None:
        """Paste image from clipboard."""
        if not is_pil_installed:
            self.error_occurred.emit("Error", "Pillow is not installed.")
            return

        try:
            # Try PIL ImageGrab first
            image = ImageGrab.grabclipboard()
            if image:
                self.log_requested.emit("Image pasted from clipboard (ImageGrab).")
                self.process_loaded_image(image, "Clipboard")
                return
        except Exception as e:
            self.log_requested.emit(f"Clipboard (ImageGrab) failed: {e}")

        # Fallback to Qt clipboard
        from PySide6.QtWidgets import QApplication

        clipboard = QApplication.clipboard()
        mime_data = clipboard.mimeData()
        if mime_data.hasImage():
            qimage = clipboard.image()
            if not qimage.isNull():
                # Convert QImage to PIL
                # In PySide6, QImage.bits() returns a memoryview or similar
                # For PySide6, we can use ImageQt or other methods,
                # but to keep it simple and consistent:
                from PIL import ImageQt

                image = ImageQt.fromqimage(qimage)
                self.log_requested.emit("Image pasted from clipboard (QImage).")
                self.process_loaded_image(image, "Clipboard (Qt)")
                return

        self.log_requested.emit("No image found in clipboard.")

    def perform_crop(self) -> None:
        """Perform cropping based on current settings and trigger OCR."""
        if self.original_image is None:
            return

        app_config = self.config_manager.get_app_config()

        try:
            if app_config.crop_mode == "drag":
                if self.manual_crop_rect:
                    w, h = self.original_image.size
                    l, t, r, b = self.manual_crop_rect
                    # Convert ratios to pixels
                    left = int(l * w)
                    top = int(t * h)
                    right = int(r * w)
                    bottom = int(b * h)
                    # Constraint
                    left = max(0, min(w, left))
                    top = max(0, min(h, top))
                    right = max(0, min(w, right))
                    bottom = max(0, min(h, bottom))
                    
                    if right > left and bottom > top:
                        self.loaded_image = self.original_image.crop((left, top, right, bottom))
                        self.image_updated.emit(self.loaded_image)
                        self.run_ocr()
                    else:
                        self.log_requested.emit("Invalid crop area.")
                else:
                    # If no crop set, show original mainly for selection
                    self.loaded_image = self.original_image.copy()
                    self.image_updated.emit(self.loaded_image)
                    self.log_requested.emit("Drag mode: Please select an area to crop.")
                
                # IMPORTANT: Do NOT fall through to percent crop
                return

            # Perform percent crop
            self.loaded_image = crop_image_by_percent(
                self.original_image,
                app_config.crop_left_percent,
                app_config.crop_top_percent,
                app_config.crop_width_percent,
                app_config.crop_height_percent,
            )

            self.image_updated.emit(self.loaded_image)
            self.run_ocr()

        except Exception as e:
            self.log_requested.emit(f"Crop error: {e}")

    def run_ocr(self) -> None:
        """Run OCR on the currently loaded (cropped) image."""
        if self.loaded_image is None:
            return

        app_config = self.config_manager.get_app_config()
        self.log_requested.emit("Running OCR...")

        try:
            # Perform OCR (AppLogic handles the heavy lifting)
            ocr_text = self.logic._perform_ocr(self.loaded_image, app_config.language)

            if ocr_text:
                result = self.logic._parse_ocr_text(ocr_text)
                # Attach images for preview/storage
                result.original_image = self.original_image
                result.cropped_image = self.loaded_image

                self.ocr_completed.emit(result)
                self.log_requested.emit(f"OCR Success (Chars: {len(ocr_text)})")

                if app_config.auto_calculate:
                    self.calculation_requested.emit()
            else:
                self.log_requested.emit("OCR failed: No text detected.")
                # Even if OCR fails, we might want to store the image
                result = OCRResult(substats=[], log_messages=[], cost=None, main_stat=None, raw_text="")
                result.original_image = self.original_image
                result.cropped_image = self.loaded_image
                self.ocr_completed.emit(result)

        except Exception as e:
            self.log_requested.emit(f"OCR Execution Error: {e}")

    def perform_crop_preview(self) -> None:
        """Generate a preview of the crop without running OCR."""
        if self.original_image is None:
            return

        app_config = self.config_manager.get_app_config()
        try:
            preview = crop_image_by_percent(
                self.original_image,
                app_config.crop_left_percent,
                app_config.crop_top_percent,
                app_config.crop_width_percent,
                app_config.crop_height_percent,
            )
            self.image_updated.emit(preview)
        except Exception as e:
            self.log_requested.emit(f"Preview error: {e}")

    def perform_image_preview_update_on_resize(self) -> None:
        """Handle preview update when window is resized."""
        if self.loaded_image:
            self.image_updated.emit(self.loaded_image)
        elif self.original_image:
            self.image_updated.emit(self.original_image)
