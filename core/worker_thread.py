"""
Worker Thread Module (PySide6)

Provides background threads for long-running tasks like OCR to prevent UI freezing.
"""

from PySide6.QtCore import QThread, Signal, QObject
from typing import List
from PIL import Image
import os
import traceback

from core.data_contracts import BatchItemResult, CropConfig
from core.app_logic import AppLogic


class WorkerSignals(QObject):
    """
    Defines the signals available from a running worker thread.
    Supported signals are:
    finished
        No data
    error
        `tuple` (exctype, value, traceback.format_exc() )
    result
        `BatchItemResult` data class
    progress
        `int` indicating current/total progress
    log
        `str` log message
    """

    finished = Signal()
    error = Signal(tuple)
    result = Signal(object)  # BatchItemResult
    progress = Signal(int, int)  # current, total
    log = Signal(str)


class OCRWorker(QThread):
    """
    Worker thread for processing a batch of images for OCR.
    """

    def __init__(self, app_logic: AppLogic, file_paths: List[str], crop_params: CropConfig, language: str):
        super().__init__()
        self.app_logic = app_logic
        self.file_paths = file_paths
        self.crop_params = crop_params
        self.language = language
        self.signals = WorkerSignals()
        self.is_cancelled = False

    def run(self):
        """
        Long-running task.
        """
        total = len(self.file_paths)
        for i, file_path in enumerate(self.file_paths):
            if self.is_cancelled:
                self.signals.log.emit("Batch processing cancelled.")
                break

            try:
                if not os.path.isfile(file_path):
                    continue

                # Load image here (in background thread)
                image = Image.open(file_path)
                image.load()

                # Apply crop if needed
                from utils.utils import crop_image_by_percent

                if self.crop_params.mode == "percent":
                    cropped_img = crop_image_by_percent(
                        image,
                        self.crop_params.left_p,
                        self.crop_params.top_p,
                        self.crop_params.width_p,
                        self.crop_params.height_p,
                    )
                else:
                    cropped_img = image.copy()

                # Perform OCR
                result = self.app_logic.perform_ocr_workflow(cropped_img, self.language)

                # Emit BatchItemResult
                self.signals.result.emit(
                    BatchItemResult(file_path=file_path, result=result, original_image=image, cropped_image=cropped_img)
                )

            except Exception as e:
                traceback.print_exc()
                exctype, value = type(e), e
                self.signals.error.emit((exctype, value, traceback.format_exc()))

            self.signals.progress.emit(i + 1, total)

        self.signals.finished.emit()

    def cancel(self):
        self.is_cancelled = True
