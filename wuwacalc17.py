import sys
import os
import webbrowser
import traceback
import logging
from typing import Any, Optional

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QMessageBox,
    QStatusBar,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QShortcut, QKeySequence, QPixmap

try:
    from PIL import Image, ImageQt
    IS_PIL_INSTALLED = True
except ImportError:
    IS_PIL_INSTALLED = False

from utils.languages import TRANSLATIONS
from utils.utils import setup_tesseract, check_and_alert_environment
from ui.event_handlers import EventHandlers
from ui.widgets.echo_tab import EchoTabWidget
from core.app_setup import AppContext
from ui.ui_constants import (
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    IMAGE_PREVIEW_MAX_WIDTH,
    IMAGE_PREVIEW_MAX_HEIGHT,
)

# Initialize Tesseract executable path
setup_tesseract()


def exception_hook(exctype, value, tb):
    """Global exception handler to catch unhandled errors."""
    traceback_details = "".join(traceback.format_exception(exctype, value, tb))
    logging.getLogger("ScoreCalculatorApp").critical(f"Unhandled exception: {traceback_details}")
    
    # Try to show a message box if QApplication exists
    if QApplication.instance():
        msg = (
            f"予期せぬエラーが発生しました:\n{value}\n\n"
            f"An unexpected error occurred.\n\n"
            f"Details (first 500 chars):\n{traceback_details[:500]}..."
        )
        QMessageBox.critical(None, "Critical Error", msg)
    else:
        print(traceback_details)
    
    sys.__excepthook__(exctype, value, tb)


sys.excepthook = exception_hook


class ScoreCalculatorApp(QMainWindow):
    """Main application class for the Wuthering Waves Echo Score Calculator."""

    def __init__(self) -> None:
        """Initialize the application components and UI."""
        super().__init__()
        # 1. Properties
        self._startup_messages = []
        self._last_displayed_image_hash = None
        self._last_image_preview = None
        self._updating_tabs = False
        self._waiting_for_character = False

        # 2. Setup Context
        self.ctx = AppContext(self)
        self.logger = self.ctx.logger
        self.logger.info("Initializing ScoreCalculatorApp...")

        # 3. Reference mapping (for convenience and backward compatibility)
        self.data_manager = self.ctx.data_manager
        self.config_manager = self.ctx.config_manager
        self.app_config = self.ctx.app_config
        self.character_manager = self.ctx.character_manager
        self.history_mgr = self.ctx.history_mgr
        self.theme_manager = self.ctx.theme_manager
        self.notebook = self.ctx.notebook
        self.ui = self.ctx.ui
        self.html_renderer = self.ctx.html_renderer
        self.score_calc = self.ctx.score_calc
        self.tab_mgr = self.ctx.tab_mgr
        self.logic = self.ctx.logic
        self.image_proc = self.ctx.image_proc

        # 4. Initialize Variables
        self._init_app_vars()
        
        # 5. Connect TabManager Signals
        self.tab_mgr.tabs_rebuild_requested.connect(self._handle_tabs_rebuild)
        self.tab_mgr.tab_label_update_requested.connect(self._handle_tab_label_update)
        self.tab_mgr.tabs_updated.connect(self.on_tabs_updated)

        # 5. Event Handlers
        self.events = EventHandlers(self, self.ctx)

        # 6. UI construction
        self.logger.info("Building UI components...")
        self.ui.create_main_layout()
        self.setCentralWidget(self.ui.main_widget)
        self.logger.info("UI layout created.")

        # 7. Signal Connections
        self.events.setup_connections()

        # 8. Final UI setup
        self.setWindowTitle("Wuthering Waves Echo Score Calculator")
        ui_config = self.config_manager.get_ui_config()
        self.resize(ui_config.window_width or WINDOW_WIDTH,
                    ui_config.window_height or WINDOW_HEIGHT)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.theme_manager.apply_theme(self.app_config.theme)
        if self.app_config.transparent_frames:
            self.theme_manager.update_frame_transparency(True)

        QTimer.singleShot(100, self._post_init_setup)
        self._setup_shortcuts()

    def _init_app_vars(self) -> None:
        """Synchronize application variables with configuration."""
        self.language = self.app_config.language
        self.current_config_key = self.app_config.current_config_key
        self.mode_var = self.app_config.mode_var
        self.character_var = ""
        self.auto_apply_main_stats = self.app_config.auto_apply_main_stats
        self.score_mode_var = self.app_config.score_mode_var
        self.crop_mode_var = self.app_config.crop_mode
        self._current_app_theme = self.app_config.theme

    def gui_log(self, message: str) -> None:
        """Display a log message in the UI log text area."""
        if getattr(self, "ui", None) and getattr(self.ui, "log_text", None):
            self.ui.log_text.append(message)
        self.logger.info(message)

    def tr(self, key: str, *args: Any) -> str:
        """Translate a string key using the current language."""
        lang_dict = TRANSLATIONS.get(self.language, TRANSLATIONS["ja"])
        text = lang_dict.get(key, key)
        return text.format(*args) if args else text

    def trigger_calculation(self) -> None:
        """Forward calculation trigger to event handlers."""
        self.events.trigger_calculation()

    def on_single_calc_completed(
        self, html: str, tab_name: str, evaluation: Any
    ) -> None:
        """Handle completion of a single echo score calculation."""
        self.ui.result_text.setHtml(html)
        self.tab_mgr.save_tab_result(tab_name, html)

    def on_batch_calc_completed(self, html: str, character: str) -> None:
        """Handle completion of batch calculation for all echoes."""
        self.ui.result_text.setHtml(html)

    def on_tabs_updated(self) -> None:
        """Slot for when the UI tabs are rebuilt or updated."""
        self.ui.update_ui_mode()
        self.tab_mgr.apply_character_main_stats(force=True)

    def _handle_tabs_rebuild(self, config_key: str, tab_names: list) -> None:
        """Called when TabManager requests a UI tab rebuild."""
        self.notebook.clear()
        
        # Calculate cost counts to decide if we need suffixes like _1, _2
        totals = {}
        for name in tab_names:
            first_digit = next((ch for ch in name if ch.isdigit()), None)
            if first_digit:
                totals[first_digit] = totals.get(first_digit, 0) + 1
        
        current_cost_indices = {}

        for tab_name in tab_names:
            cost_num = next((ch for ch in tab_name if ch.isdigit()), "1")
            total_for_cost = totals.get(cost_num, 1)
            current_idx = current_cost_indices.get(cost_num, 0) + 1
            current_cost_indices[cost_num] = current_idx

            cost_key = (cost_num if total_for_cost == 1 
                        else f"{cost_num}_{current_idx}")

            # Create the widget (UI responsibility)
            main_opts = self.data_manager.main_stat_options.get(
                cost_num, ["HP", "ATK", "DEF"]
            )
            sub_opts = list(self.data_manager.substat_max_values.keys())
            tab_widget = EchoTabWidget(cost_num, main_opts, sub_opts, self.tr)
            
            # Label
            label = self.tab_mgr._generate_tab_label(tab_name)
            self.notebook.addTab(tab_widget, label)
            
            # Register back to manager
            self.tab_mgr.register_tab_widget(tab_name, tab_widget, cost_num, cost_key)
            
        self.tab_mgr.finalize_rebuild()

    def _handle_tab_label_update(self, index: int, label: str) -> None:
        """Update a specific tab's label."""
        if index < self.notebook.count():
            self.notebook.setTabText(index, label)

    def _switch_to_tab(self, tab_name: str) -> None:
        """Switch the UI notebook to the specified tab name."""
        config_key = self.app_config.current_config_key
        tab_names = self.data_manager.tab_configs.get(config_key, [])
        if tab_name in tab_names:
            idx = tab_names.index(tab_name)
            self.notebook.setCurrentIndex(idx)

    def show_tab_image(self, tab_name: str) -> None:
        """Display the cropped image associated with a specific tab."""
        data = self.tab_mgr.get_tab_image(tab_name)
        if data:
            self.update_image_preview(data.cropped)

    def show_tab_result(self, tab_name: str) -> None:
        """Display the stored calculation result for a specific tab."""
        html = self.tab_mgr.get_tab_result(tab_name)
        if html:
            self.ui.result_text.setHtml(html)
        else:
            self.ui.result_text.clear()

    def check_character_selected(self, quiet: bool = False) -> bool:
        """Verify if a character is selected; if not, prompt the user."""
        if not self.character_var:
            if not quiet:
                msg = (
                    f"<h3 style='color: orange;'>"
                    f"{self.tr('waiting_for_character')}</h3>"
                )
                self.ui.result_text.setHtml(msg)
            self._waiting_for_character = True
            return False
        return True

    def _setup_shortcuts(self) -> None:
        """Initialize keyboard shortcuts."""
        paste_seq = QKeySequence("Ctrl+V")
        calc_seq = QKeySequence("Ctrl+Return")
        f5_seq = QKeySequence("F5")
        save_seq = QKeySequence("Ctrl+S")
        clear_seq = QKeySequence("Ctrl+R")

        QShortcut(paste_seq, self).activated.connect(
            self.events.paste_from_clipboard
        )
        QShortcut(calc_seq, self).activated.connect(
            self.events.trigger_calculation
        )
        QShortcut(f5_seq, self).activated.connect(
            self.events.trigger_calculation
        )
        QShortcut(save_seq, self).activated.connect(
            self.export_result_to_txt
        )
        QShortcut(clear_seq, self).activated.connect(self.clear_all)

    def set_current_as_equipped(self) -> None:
        """Save current tab's data as equipped echo for this character."""
        if not self.character_var:
            msg = self.tr("waiting_for_character")
            QMessageBox.warning(self, self.tr("warning"), msg)
            return

        tab_name = self.get_selected_tab_name()
        if not tab_name:
            return

        entry = self.tab_mgr.extract_tab_data(tab_name)
        if not entry or not entry.main_stat:
            error_msg = self.tr("main_stat_missing", tab_name)
            QMessageBox.warning(self, self.tr("warning"), error_msg)
            return

        self.character_manager.save_equipped_echo(
            self.character_var, tab_name, entry
        )
        self.gui_log(f"Set as Equipped: {self.character_var} - {tab_name}")
        QMessageBox.information(
            self, self.tr("info"), self.tr("save_msg", tab_name)
        )

        # Re-trigger calculation to show the updated comparison
        self.trigger_calculation()

    def export_result_to_txt(self) -> None:
        """Export the current calculation result to a text file."""
        if self.tab_mgr:
            self.tab_mgr.export_to_txt(self, self.ui.result_text.toPlainText())

    def clear_all(self) -> None:
        """Reset all echo data and clear the UI."""
        if self.tab_mgr:
            self.tab_mgr.clear_all()
            self.ui.result_text.clear()
            self.update_image_preview(None)

    def clear_current_tab(self) -> None:
        """Clear data for the currently selected tab."""
        if self.tab_mgr:
            tab_name = self.get_selected_tab_name()
            if tab_name:
                self.tab_mgr.clear_tab(tab_name)
            self.ui.result_text.clear()

    def update_image_preview(self, image: Optional["Image.Image"]) -> None:
        """Update the image preview label with a new PIL Image."""
        ui = getattr(self, "ui", None)
        lbl = getattr(ui, "image_label", None)

        if not IS_PIL_INSTALLED or lbl is None or image is None:
            if lbl:
                lbl.setText(self.tr("no_image"))
                lbl.setPixmap(QPixmap())
            return

        qim = ImageQt.ImageQt(image)
        pixmap = QPixmap.fromImage(qim)
        scaled = pixmap.scaled(
            IMAGE_PREVIEW_MAX_WIDTH,
            IMAGE_PREVIEW_MAX_HEIGHT,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        lbl.setPixmap(scaled)

    def _post_init_setup(self) -> None:
        """Late-stage initialization after UI is shown."""
        self.tab_mgr.update_tabs()
        self.events.on_profiles_updated()
        check_and_alert_environment(self.gui_log)
        
        if not IS_PIL_INSTALLED:
             QMessageBox.critical(
                 self, 
                 self.tr("error"), 
                 "Pillow (PIL) is not installed. Image processing functions will not work.\n"
                 "Please install it using: pip install Pillow"
             )

    def show_duplicate_entries(self) -> None:
        """Check for and log duplicate echo entries."""
        entries = self.tab_mgr.get_all_echo_entries()
        dup_ids = self.tab_mgr.find_duplicate_entries(entries)
        if dup_ids:
            self.gui_log(f"Duplicate detected: {dup_ids}")

    def show_ocr_error_message(self, title: str, message: str) -> None:
        """Show a critical error message box for OCR failures."""
        QMessageBox.critical(self, title, message)

    def show_error_message(self, title: str, message: str) -> None:
        """Show a standard error message box."""
        QMessageBox.critical(self, title, message)

    def show_info_message(self, title: str, message: str) -> None:
        """Show an informational message box."""
        QMessageBox.information(self, title, message)

    def refresh_results_display(self) -> None:
        """Refreshes the current display and all stored tab results."""
        current_html = self.ui.result_text.toHtml()

        # Update current display
        updated_current = self.html_renderer.refresh_html_style(current_html)
        if updated_current != current_html:
            self.ui.result_text.setHtml(updated_current)

        # Update cached results for all tabs
        for tab_name in list(self.tab_mgr._tab_results.keys()):
            data = self.tab_mgr._tab_results[tab_name]
            content = getattr(data, "content", None)
            if content:
                updated = self.html_renderer.refresh_html_style(content)
                self.tab_mgr.save_tab_result(tab_name, updated)

        # Ensure current tab's specific data (image/result) is also synced
        tab_name = self.get_selected_tab_name()
        if tab_name:
            self.show_tab_result(tab_name)
            self.show_tab_image(tab_name)

    def get_selected_tab_name(self) -> Optional[str]:
        """Proxy for tab_mgr.get_selected_tab_name using current notebook state."""
        return self.tab_mgr.get_selected_tab_name(self.notebook.currentIndex())

    def _open_readme(self) -> None:
        """Opens the help HTML file in the default web browser."""
        base_dir = os.path.dirname(os.path.abspath(__file__))
        help_path = os.path.join(base_dir, "help.html")
        if os.path.exists(help_path):
            webbrowser.open(f"file:///{help_path}")
        else:
            self.gui_log(f"Help file not found: {help_path}")

    def update_text_color(self, color: str) -> None:
        """Update global main text color and refresh display."""
        self.theme_manager.update_text_color(color)
        self.html_renderer.set_text_color(color)
        self.refresh_results_display()

    def apply_theme(self, theme_name: str) -> None:
        """Apply a pre-defined color theme to the entire application."""
        self.theme_manager.apply_theme(theme_name)
        self.html_renderer.set_text_color(self.app_config.text_color)
        self._refresh_ui_styles()

    def _refresh_ui_styles(self) -> None:
        """Refreshes UI shadows and updates the main results display."""
        self.theme_manager.refresh_global_shadows()
        self.refresh_results_display()

    def update_input_bg_color(self, color: str) -> None:
        """Update the background color for input widgets."""
        self.theme_manager.update_input_bg_color(color)

    def update_app_font(self, font: str) -> None:
        """Update the primary application font."""
        self.theme_manager.update_app_font(font)
        self.refresh_results_display()

    def update_frame_transparency(self, transparent: bool) -> None:
        """Toggle transparency for UI frame components."""
        self.theme_manager.update_frame_transparency(transparent)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ScoreCalculatorApp()
    window.show()
    sys.exit(app.exec())
