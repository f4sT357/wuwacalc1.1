from typing import Any
from ui.handlers.base import BaseHandler
from PySide6.QtWidgets import QMessageBox, QFileDialog
from core.data_contracts import OCRResult, BatchItemResult

class OCRHandler(BaseHandler):
    """Handles OCR results, image imports, and clipboard interaction."""
    
    def __init__(self, app: Any, ctx: Any):
        super().__init__(app, ctx)
        self._ocr_trigger_character = None
        self._temp_ocr_result = None
        self._batch_assigned_tabs = []

    def on_ocr_completed(self, result: Any) -> None:
        ocr_data = result if isinstance(result, OCRResult) else result.result
        self.ui.display_ocr_overlay(ocr_data)

        if not self.app.character_var:
            self._temp_ocr_result = result
            self.app.gui_log("OCR data cached. Waiting for character selection.")
            QMessageBox.information(
                self.app, self.app.tr("info"),
                self.app.tr("ocr_deferred_msg", "OCR完了。適用先のキャラクターを選択してください。")
            )
            return

        if (self._ocr_trigger_character is not None
                and self.app.character_var != self._ocr_trigger_character):
            msg = self.app.tr("ocr_char_mismatch_warning")
            reply = QMessageBox.question(
                self.app, self.app.tr("warning"), msg,
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )

            if reply == QMessageBox.No:
                self.app.gui_log(f"OCR result discarded (Character changed).")
                return

        if isinstance(result, OCRResult):
            self._apply_ocr_result(result, result.original_image, result.cropped_image)
        elif isinstance(result, BatchItemResult):
            self._apply_ocr_result(
                result.result, result.original_image, result.cropped_image, is_batch=True
            )

    def _apply_ocr_result(self, ocr_data: Any, original_img: Any, cropped_img: Any, is_batch: bool = False) -> None:
        for msg in ocr_data.log_messages:
            self.app.gui_log(msg)

        target_tab = self.tab_mgr.find_best_tab_match(
            ocr_data.cost, ocr_data.main_stat, self.app.character_var
        )
        
        # If batch mode, prefer non-assigned tabs matching cost
        if is_batch and target_tab in self._batch_assigned_tabs:
            target_tab = self.tab_mgr.get_next_available_tab(
                exclude_tabs=self._batch_assigned_tabs, cost=ocr_data.cost
            )

        if not target_tab:
            if is_batch:
                target_tab = self.tab_mgr.get_next_available_tab(
                    exclude_tabs=self._batch_assigned_tabs, cost=ocr_data.cost
                )
            else:
                target_tab = self.app.get_selected_tab_name()

        if target_tab:
            if is_batch:
                self._batch_assigned_tabs.append(target_tab)
            else:
                self.app._switch_to_tab(target_tab)

            self.app.gui_log(f"Applying result to tab: {target_tab}")
            self.tab_mgr.apply_ocr_result_to_tab(target_tab, ocr_data)
            self.tab_mgr.save_tab_image(target_tab, original_img, cropped_img)
            
            if not is_batch:
                self.ui.display_ocr_overlay(ocr_data)

            if not is_batch and self.app.app_config.auto_calculate:
                from PySide6.QtCore import QTimer
                QTimer.singleShot(100, self.app.trigger_calculation)

    def import_image(self) -> None:
        self.app.check_character_selected(quiet=False)
        self._ocr_trigger_character = self.app.character_var
        file_paths, _ = QFileDialog.getOpenFileNames(
            self.app, self.app.tr("select_image_file"), "",
            f"{self.app.tr('image_files')} (*.png *.jpg *.jpeg *.bmp *.gif);;"
            f"{self.app.tr('all_files')} (*.*)"
        )
        if file_paths:
            if len(file_paths) > 5:
                QMessageBox.warning(
                    self.app, self.app.tr("info"),
                    self.app.tr("batch_processing_limit_reached")
                )
                file_paths = file_paths[:5]
            
            self._batch_assigned_tabs = []
            self.image_proc.process_images_from_paths(file_paths)

    def handle_dropped_files(self, paths: list) -> None:
        """Process images that were dropped onto the UI."""
        if not paths:
            return
        self.app.check_character_selected(quiet=False)
        self._ocr_trigger_character = self.app.character_var
        
        if len(paths) > 5:
            QMessageBox.warning(
                self.app, self.app.tr("info"),
                self.app.tr("batch_processing_limit_reached")
            )
            paths = paths[:5]
            
        self._batch_assigned_tabs = []
        self.image_proc.process_images_from_paths(paths)

    def paste_from_clipboard(self) -> None:
        self.app.check_character_selected(quiet=True)
        self._ocr_trigger_character = self.app.character_var
        self.image_proc.paste_from_clipboard()

    def check_deferred_ocr(self) -> None:
        if self._temp_ocr_result:
            result = self._temp_ocr_result
            self.app.gui_log("Applying cached OCR data...")
            self.on_ocr_completed(result)
            self._temp_ocr_result = None
