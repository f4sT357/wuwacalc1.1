from typing import Any
from ui.handlers.base import BaseHandler
from PySide6.QtWidgets import QMessageBox
from PySide6.QtCore import QTimer
from utils.constants import TIMER_SAVE_CONFIG_INTERVAL

class ConfigHandler(BaseHandler):
    """Handles application settings, localization, and theme changes."""
    
    def __init__(self, app: Any, ctx: Any):
        super().__init__(app, ctx)
        self._save_timer = QTimer()
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self.actual_save_config)

    def on_language_change(self, text: str) -> None:
        if text != self.app.app_config.language:
            self.app.language = text
            self.app.html_renderer.language = text
            self.config_manager.update_app_setting('language', text)
            self.save_config()
            self.ui.retranslate_ui()
            self.tab_mgr.retranslate_tabs(text)
            self.ui.filter_characters_by_config()
            self.app.status_bar.showMessage(self.app.tr("settings_loaded"), 5000)

    def on_mode_change(self, mode: str) -> None:
        self.app.mode_var = mode
        self.config_manager.update_app_setting('mode_var', mode)
        self.ui.update_ui_mode()
        self.save_config()

    def on_auto_main_change(self, checked: bool) -> None:
        self.app.auto_apply_main_stats = checked
        self.config_manager.update_app_setting('auto_apply_main_stats', checked)
        self.save_config()

    def on_auto_calculate_change(self, checked: bool) -> None:
        self.config_manager.update_app_setting('auto_calculate', checked)
        self.save_config()

    def on_score_mode_change(self, mode: str) -> None:
        self.app.score_mode_var = mode
        self.config_manager.update_app_setting('score_mode_var', mode)
        self.save_config()

    def on_calc_method_changed(self) -> None:
        enabled_methods = {
            "normalized": self.ui.cb_method_normalized.isChecked(),
            "ratio": self.ui.cb_method_ratio.isChecked(),
            "roll": self.ui.cb_method_roll.isChecked(),
            "effective": self.ui.cb_method_effective.isChecked(),
            "cv": self.ui.cb_method_cv.isChecked()
        }

        if not any(enabled_methods.values()):
            QMessageBox.warning(self.app, self.app.tr("warning"), self.app.tr("no_methods_selected"))
            sender = self.app.sender()
            if sender: sender.setChecked(True)
            return

        self.config_manager.update_app_setting('enabled_calc_methods', enabled_methods)
        self.save_config()

    def on_crop_mode_change(self, mode: str) -> None:
        self.app.crop_mode_var = mode
        self.config_manager.update_app_setting('crop_mode', mode)
        self.save_config()
        self.ui.image_label.set_drag_enabled(mode == "drag")
        self.ui.btn_apply_crop.setVisible(mode == "drag")
        
        # In percent mode, show the preview box
        if mode == "percent":
            c = self.config_manager.get_app_config()
            self.ui.image_label.set_crop_preview(
                c.crop_left_percent, c.crop_top_percent, 
                c.crop_width_percent, c.crop_height_percent
            )
        else:
            self.ui.image_label.set_crop_preview(0, 0, 0, 0)

    def on_crop_percent_change(self, text: str) -> None:
        try:
            sender = self.app.sender()
            value = float(text) if text else 0.0
            if sender == self.ui.entry_crop_l:
                self.config_manager.update_app_setting('crop_left_percent', value)
                self.ui.slider_crop_l.setValue(int(value))
            elif sender == self.ui.entry_crop_t:
                self.config_manager.update_app_setting('crop_top_percent', value)
                self.ui.slider_crop_t.setValue(int(value))
            elif sender == self.ui.entry_crop_w:
                self.config_manager.update_app_setting('crop_width_percent', value)
                self.ui.slider_crop_w.setValue(int(value))
            elif sender == self.ui.entry_crop_h:
                self.config_manager.update_app_setting('crop_height_percent', value)
                self.ui.slider_crop_h.setValue(int(value))
            self.save_config()
            self.app.events.schedule_crop_preview()
            
            # Update live preview box
            c = self.config_manager.get_app_config()
            self.ui.image_label.set_crop_preview(
                c.crop_left_percent, c.crop_top_percent, 
                c.crop_width_percent, c.crop_height_percent
            )
        except ValueError:
            pass

    def on_crop_slider_change(self, value: int) -> None:
        sender = self.app.sender()
        if not sender: return
        obj_name = sender.objectName()
        if obj_name == "slider_crop_l": self.ui.entry_crop_l.setText(str(value))
        elif obj_name == "slider_crop_t": self.ui.entry_crop_t.setText(str(value))
        elif obj_name == "slider_crop_w": self.ui.entry_crop_w.setText(str(value))
        elif obj_name == "slider_crop_h": self.ui.entry_crop_h.setText(str(value))

    def cycle_theme(self) -> None:
        themes = ["dark", "light", "clear"]
        current = self.app.ctx.theme_manager.get_current_theme()
        new_theme = themes[(themes.index(current) + 1) % len(themes)] if current in themes else "dark"
        self.app.ctx.theme_manager.apply_theme(new_theme)
        self.config_manager.update_app_setting('theme', new_theme)
        self.save_config()

    def save_config(self) -> None:
        self._save_timer.start(TIMER_SAVE_CONFIG_INTERVAL)

    def actual_save_config(self) -> None:
        self.config_manager.update_app_setting('character_var', self.app.character_var)
        self.config_manager.update_app_setting('theme', self.app.ctx.theme_manager.get_current_theme())
        self.config_manager.save()
