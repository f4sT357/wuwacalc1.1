from __future__ import annotations
import logging
from typing import Any, TYPE_CHECKING

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QInputDialog

from utils.constants import (
    TIMER_CROP_PREVIEW_INTERVAL,
    TIMER_RESIZE_PREVIEW_INTERVAL
)

if TYPE_CHECKING:
    from core.app_setup import AppContext

from ui.handlers.ocr_handler import OCRHandler
from ui.handlers.config_handler import ConfigHandler
from ui.handlers.character_handler import CharacterHandler
from ui.handlers.calculation_handler import CalculationHandler


class EventHandlers:
    """Class responsible for coordinating specialized event handlers."""

    def __init__(self, app: Any, ctx: AppContext) -> None:
        self.app = app
        self.ctx = ctx
        self.logger = logging.getLogger(__name__)

        # Specialized Handlers
        self.ocr_handler = OCRHandler(app, ctx)
        self.config_handler = ConfigHandler(app, ctx)
        self.char_handler = CharacterHandler(app, ctx)
        self.calc_handler = CalculationHandler(app, ctx)

        # Integration with other modules
        self.ui = ctx.ui
        self.config_manager = ctx.config_manager
        self.data_manager = ctx.data_manager
        self.tab_mgr = ctx.tab_mgr
        self.character_manager = ctx.character_manager
        self.image_proc = ctx.image_proc
        self.score_calc = ctx.score_calc
        self.logic = ctx.logic

        # Timer references for debouncing in ImageProc context
        self._crop_preview_timer = QTimer()
        self._crop_preview_timer.setSingleShot(True)
        self._crop_preview_timer.timeout.connect(self.image_proc.perform_crop_preview)

        self._resize_preview_timer = QTimer()
        self._resize_preview_timer.setSingleShot(True)
        self._resize_preview_timer.timeout.connect(
            self.image_proc.perform_image_preview_update_on_resize
        )

    def setup_connections(self) -> None:
        """Set up all signal and slot connections for the application."""
        # Logic signals
        self.logic.log_message.connect(self.app.gui_log)
        self.logic.ocr_error.connect(self.app.show_ocr_error_message)
        self.logic.info_message.connect(self.app.show_info_message)

        # ScoreCalc signals
        self.score_calc.log_requested.connect(self.app.gui_log)
        self.score_calc.error_occurred.connect(self.app.show_error_message)
        self.score_calc.single_calculation_completed.connect(self.app.on_single_calc_completed)
        self.score_calc.batch_calculation_completed.connect(self.app.on_batch_calc_completed)

        # TabMgr signals
        self.tab_mgr.log_requested.connect(self.app.gui_log)
        self.tab_mgr.tabs_updated.connect(self.app.on_tabs_updated)

        # ImageProc signals
        self.image_proc.ocr_completed.connect(self.ocr_handler.on_ocr_completed)
        self.image_proc.log_requested.connect(self.app.gui_log)
        self.image_proc.error_occurred.connect(self.app.show_error_message)
        self.image_proc.image_updated.connect(self.app.update_image_preview)
        self.image_proc.calculation_requested.connect(self.trigger_calculation)

        # UI signals
        self.app.notebook.currentChanged.connect(self.on_tab_changed)
        self.character_manager.profiles_updated.connect(self.char_handler.on_profiles_updated)
        self.character_manager.character_registered.connect(self.char_handler.on_character_registered)

        self.ui.config_combo.currentTextChanged.connect(self.on_config_change)
        self.ui.character_combo.currentIndexChanged.connect(self.char_handler.on_character_change)
        self.ui.lang_combo.currentTextChanged.connect(self.config_handler.on_language_change)
        self.ui.rb_manual.toggled.connect(lambda c: self.config_handler.on_mode_change("manual") if c else None)
        self.ui.rb_ocr.toggled.connect(lambda c: self.config_handler.on_mode_change("ocr") if c else None)
        self.ui.cb_auto_main.toggled.connect(self.config_handler.on_auto_main_change)
        self.ui.rb_batch.toggled.connect(lambda c: self.config_handler.on_score_mode_change("batch") if c else None)
        self.ui.rb_single.toggled.connect(lambda c: self.config_handler.on_score_mode_change("single") if c else None)

        self.ui.image_label.selection_completed.connect(self.image_proc.set_manual_crop_rect)
        self.ui.image_label.files_dropped.connect(self.ocr_handler.handle_dropped_files)
        self.ui.image_label.box_clicked.connect(self.on_ocr_box_clicked)

        for method, cb in self.ui.method_checkboxes.items():
            cb.toggled.connect(self.config_handler.on_calc_method_changed)

    # --- Delegated Methods (maintained for backward compatibility where signals expect them on 'events' object) ---

    def trigger_calculation(self) -> None:
        self.calc_handler.trigger_calculation()

    def on_tab_changed(self, index: int) -> None:
        if index < 0 or getattr(self.app, "_updating_tabs", False):
            return
        tab_name = self.app.get_selected_tab_name()
        if tab_name:
            self.app.show_tab_image(tab_name)
            self.app.show_tab_result(tab_name)

    def on_config_change(self, text: str) -> None:
        self.app.current_config_key = text
        self.config_manager.update_app_setting('current_config_key', text)
        if not getattr(self.app, "_updating_tabs", False):
            self.tab_mgr.update_tabs()
            self.tab_mgr.apply_character_main_stats(character=self.app.character_var)
            self.ui.filter_characters_by_config()
            self.save_config()

    def save_config(self) -> None:
        self.config_handler.save_config()

    def schedule_crop_preview(self) -> None:
        self._crop_preview_timer.start(TIMER_CROP_PREVIEW_INTERVAL)

    def schedule_image_preview_update_on_resize(self, *args: Any) -> None:
        self._resize_preview_timer.start(TIMER_RESIZE_PREVIEW_INTERVAL)

    def paste_from_clipboard(self) -> None:
        self.ocr_handler.paste_from_clipboard()

    def import_image(self) -> None:
        self.ocr_handler.import_image()

    def generate_scoreboard(self) -> None:
        self.calc_handler.generate_scoreboard()

    def on_auto_calculate_change(self, checked: bool) -> None:
        self.config_handler.on_auto_calculate_change(checked)

    def on_crop_mode_change(self, mode: str) -> None:
        self.config_handler.on_crop_mode_change(mode)

    def apply_selection_to_crop(self) -> None:
        """Apply the drag-selected area from the image label to the percentage crop settings."""
        pct = self.ui.image_label.last_selection_pct
        if not pct:
            return
        
        l, t, r, b = pct
        w = r - l
        h = b - t
        
        # Convert to 0-100%
        lp, tp, wp, hp = l * 100.0, t * 100.0, w * 100.0, h * 100.0
        
        # Disable signals temporarily to avoid multiple crop previews
        self.ui.entry_crop_l.blockSignals(True)
        self.ui.entry_crop_t.blockSignals(True)
        self.ui.entry_crop_w.blockSignals(True)
        self.ui.entry_crop_h.blockSignals(True)
        
        self.ui.entry_crop_l.setText(f"{lp:.1f}")
        self.ui.entry_crop_t.setText(f"{tp:.1f}")
        self.ui.entry_crop_w.setText(f"{wp:.1f}")
        self.ui.entry_crop_h.setText(f"{hp:.1f}")
        
        # Also update sliders
        self.ui.slider_crop_l.setValue(int(lp))
        self.ui.slider_crop_t.setValue(int(tp))
        self.ui.slider_crop_w.setValue(int(wp))
        self.ui.slider_crop_h.setValue(int(hp))

        self.ui.entry_crop_l.blockSignals(False)
        self.ui.entry_crop_t.blockSignals(False)
        self.ui.entry_crop_w.blockSignals(False)
        self.ui.entry_crop_h.blockSignals(False)
        
        # Manually update config and trigger preview once
        self.config_manager.update_app_setting('crop_left_percent', lp)
        self.config_manager.update_app_setting('crop_top_percent', tp)
        self.config_manager.update_app_setting('crop_width_percent', wp)
        self.config_manager.update_app_setting('crop_height_percent', hp)
        self.save_config()
        self.ui.image_label.set_crop_preview(lp, tp, wp, hp)
        self.logger.info(f"Applied drag selection to crop settings: L={lp:.1f}% T={tp:.1f}% W={wp:.1f}% H={hp:.1f}%")

    def on_crop_percent_change(self, text: str) -> None:
        self.config_handler.on_crop_percent_change(text)

    def on_crop_slider_change(self, value: int) -> None:
        self.config_handler.on_crop_slider_change(value)

    def on_profiles_updated(self) -> None:
        self.char_handler.on_profiles_updated()

    def open_char_settings_new(self) -> None:
        from ui.dialogs import CharSettingDialog
        CharSettingDialog(self.app, self.character_manager.register_character).exec()

    def open_char_settings_edit(self) -> None:
        from ui.dialogs import CharSettingDialog
        target_char = self.app.character_var
        if not target_char:
            all_chars = self.character_manager.get_all_characters(self.app.language)
            if not all_chars: return
            items = [name for name, internal in all_chars]
            item, ok = QInputDialog.getItem(
                self.app, self.app.tr("select_character"),
                self.app.tr("select_character_to_edit"), items, 0, False
            )
            if ok and item:
                target_char = next((internal for name, internal in all_chars if name == item), None)
            else: return

        p = self.character_manager.get_character_profile(target_char)
        if p: CharSettingDialog(self.app, self.character_manager.register_character, profile=p).exec()

    def open_display_settings(self) -> None:
        from ui.dialogs import DisplaySettingsDialog
        DisplaySettingsDialog(self.app).exec()

    def open_history(self) -> None:
        from ui.dialogs import HistoryDialog
        HistoryDialog(self.app, self.app.ctx.history_mgr).exec()

    def open_image_preprocessing_settings(self) -> None:
        from ui.dialogs import ImagePreprocessingSettingsDialog
        ImagePreprocessingSettingsDialog(self.app).exec()

    def on_ocr_box_clicked(self, typeinfo: str, key_idx: Any) -> None:
        """Handle click on an OCR bounding box to focus the corresponding UI field."""
        if typeinfo == "sub":
            tab_name = self.app.get_selected_tab_name()
            tab_widget = self.tab_mgr.get_tab_widget(tab_name)
            if tab_widget and isinstance(key_idx, int) and key_idx < len(tab_widget.sub_entries):
                _, le = tab_widget.sub_entries[key_idx]
                le.setFocus()
                le.selectAll()
        elif typeinfo == "main":
            tab_name = self.app.get_selected_tab_name()
            tab_widget = self.tab_mgr.get_tab_widget(tab_name)
            if tab_widget:
                if key_idx == "main_stat":
                    tab_widget.main_combo.setFocus()
