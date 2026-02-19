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
        from ui.dialogs.ocr_verification import OCRVerificationDialog
        
        ocr_data = result if isinstance(result, OCRResult) else result.result
        original_img = result.original_image if hasattr(result, "original_image") else ocr_data.original_image
        cropped_img = result.cropped_image if hasattr(result, "cropped_image") else ocr_data.cropped_image

        if not self.app.character_var:
            self._temp_ocr_result = result
            self.app.gui_log("OCR data cached. Waiting for character selection.")
            QMessageBox.information(
                self.app, self.app.tr("info"),
                self.app.tr("ocr_deferred_msg", "OCR完了。適用先のキャラクターを選択してください。")
            )
            return

        # Show verification dialog
        dialog = OCRVerificationDialog(self.app, ocr_data, cropped_img)
        if dialog.exec():
            # User confirmed
            verified_data = dialog.get_verified_data()
            self._apply_ocr_result(verified_data, original_img, cropped_img, 
                                  is_batch=isinstance(result, BatchItemResult))
        else:
            self.app.gui_log("OCR result verification cancelled by user.")

    def _apply_ocr_result(self, ocr_data: Any, original_img: Any, cropped_img: Any, is_batch: bool = False) -> None:
        for msg in ocr_data.log_messages:
            self.app.gui_log(msg)

        # Strategy 1: Check for duplicates in other tabs
        existing_tab = self.tab_mgr.find_tab_by_echo_data(ocr_data)
        
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
            # Check if we are moving an existing echo
            if existing_tab and existing_tab != target_tab and not is_batch:
                from PySide6.QtWidgets import QMessageBox
                old_label = self.tab_mgr._generate_tab_label(existing_tab)
                new_label = self.tab_mgr._generate_tab_label(target_tab)
                
                reply = QMessageBox.question(
                    self.app, self.app.tr("duplicate_found"),
                    self.app.tr("move_echo_msg", 
                        f"この音骸は既に「{old_label}」に登録されています。\n「{new_label}」へ移動しますか？"),
                    QMessageBox.Yes | QMessageBox.No
                )
                
                if reply == QMessageBox.Yes:
                    self.app.gui_log(f"Moving echo from {existing_tab} to {target_tab}")
                    self.tab_mgr.clear_tab(existing_tab)
                else:
                    self.app.gui_log("OCR application cancelled: Duplicate echo already exists.")
                    return

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
