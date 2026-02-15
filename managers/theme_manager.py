"""
Theme Management Module (PySide6)

Handles application-wide styling, color themes, and dynamic 
element-based accent colors.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtWidgets import QApplication, QStyleFactory
from utils.constants import THEME_COLORS

if TYPE_CHECKING:
    from wuwacalc17 import ScoreCalculatorApp


class ThemeManager:
    """Manages UI themes and dynamic styling for the application."""

    def __init__(self, app_instance: ScoreCalculatorApp):
        self.app = app_instance
        self.logger = logging.getLogger(__name__)

    def _hex_to_rgba(self, hex_color: str, alpha: float) -> str:
        """Convert hex color string to CSS rgba format."""
        hex_color = hex_color.lstrip("#")
        if len(hex_color) == 6:
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            return f"rgba({r}, {g}, {b}, {alpha})"
        return hex_color

    def _apply_theme_stylesheet(self, theme_name: str) -> None:
        """Generate and apply the global CSS stylesheet based on current state."""
        colors = THEME_COLORS.get(theme_name, THEME_COLORS["light"])
        is_transparent = self.app.app_config.transparent_frames
        config = self.app.app_config

        # 1. Determine Accent Color
        if config.accent_mode == "custom":
            c_accent = config.custom_accent_color
        else:
            # element-based (auto)
            profile = self.app.character_manager.get_character_profile(self.app.character_var)
            element = profile.element if profile else "default"
            from core.scoreboard_generator import ScoreboardGenerator
            theme_cfg = ScoreboardGenerator.ELEMENT_THEMES.get(
                element, ScoreboardGenerator.DEFAULT_THEME
            )
            acc_rgb = theme_cfg["accent"]
            c_accent = f"rgb({acc_rgb[0]}, {acc_rgb[1]}, {acc_rgb[2]})"

        c_bg = colors["background"]
        c_input = config.custom_input_bg_color or colors["input_bg"]
        c_btn = colors["button_bg"]
        c_border = colors["border"]
        group_border = f"2px solid {c_accent}"
        
        font_family = config.app_font
        font_style = f"font-family: '{font_family}';" if font_family else ""

        if is_transparent:
            text_edit_bg = self._hex_to_rgba(colors["input_bg"], 0.15)
            tab_pane_bg = self._hex_to_rgba(colors["background"], 0.1)
            tab_pane_border = f"1px solid {self._hex_to_rgba(c_accent, 0.3)}"
            c_border = self._hex_to_rgba(c_accent, 0.4)
            group_border = f"2px solid {self._hex_to_rgba(c_accent, 0.5)}"
        else:
            text_edit_bg = c_input
            tab_pane_bg = c_bg
            tab_pane_border = f"1px solid {c_accent}"

        stylesheet = f"""
            QMainWindow {{ 
                background-color: {colors['background']};
                color: {self.app.app_config.text_color}; 
                {font_style} 
            }}
            QWidget {{ 
                background-color: {c_bg}; 
                color: {self.app.app_config.text_color}; 
                {font_style} 
            }}
            QLineEdit, QSpinBox, QDoubleSpinBox {{ 
                background-color: {c_input}; 
                color: {self.app.app_config.text_color}; 
                border: 1px solid {c_border}; 
                {font_style} 
            }}
            QTextEdit {{
                background-color: {text_edit_bg}; 
                color: {self.app.app_config.text_color}; 
                border: 1px solid {c_border}; 
                {font_style}
            }}
            QPushButton {{ 
                background-color: {c_btn}; 
                color: {self.app.app_config.text_color}; 
                border: 1px solid {c_border}; 
                border-radius: 4px;
                padding: 5px; 
                {font_style} 
            }}
            QPushButton:hover {{ 
                background-color: {self._hex_to_rgba(c_accent, 0.2)}; 
                border: 1px solid {c_accent};
            }}
            QTabWidget::pane {{ 
                border: {tab_pane_border}; 
                background-color: {tab_pane_bg}; 
                border-radius: 4px;
            }}
            QTabBar::tab {{ 
                background: {colors['tab_bg']}; 
                color: {self.app.app_config.text_color}; 
                padding: 8px 12px; 
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                {font_style} 
            }}
            QTabBar::tab:selected {{ 
                background: {c_accent}; 
                color: white;
                font-weight: bold;
            }}
            QGroupBox {{ 
                border: {group_border}; 
                border-radius: 8px;
                margin-top: 15px; 
                padding-top: 10px;
                background-color: {self._hex_to_rgba(c_bg, 0.5) if is_transparent else c_bg}; 
                {font_style} 
                font-weight: bold;
            }}
            QGroupBox::title {{ 
                subcontrol-origin: margin; 
                subcontrol-position: top left; 
                padding: 0 10px; 
                color: {c_accent};
                background-color: transparent; 
            }}
            QComboBox {{ 
                background-color: {c_input}; 
                color: {self.app.app_config.text_color}; 
                border: 1px solid {c_border}; 
                border-radius: 3px;
                {font_style} 
            }}
        """
        q_app = QApplication.instance()
        if q_app:
            q_app.setStyleSheet(stylesheet)

    def update_app_font(self, font_family: str) -> None:
        """Update the application font and refresh styles."""
        self.app.config_manager.update_app_setting("app_font", font_family)
        self.apply_theme(self.get_current_theme())

    def get_current_theme(self) -> str:
        """Return the identifier of the currently active theme."""
        return getattr(self.app, "_current_app_theme", "dark")

    def apply_theme(self, theme_name: str) -> None:
        """Apply a named theme and refresh the global stylesheet."""
        try:
            self.app._current_app_theme = theme_name
            self.app.config_manager.update_app_setting("theme", theme_name)
            
            # Sync text color from theme defaults
            colors = THEME_COLORS.get(theme_name, THEME_COLORS["dark"])
            self.app.app_config.text_color = colors.get("text", "#ffffff")
            
            if QApplication.instance():
                QApplication.setStyle(QStyleFactory.create("Fusion"))
                self._apply_theme_stylesheet(theme_name)
        except Exception as e:
            self.logger.exception(f"Error applying theme: {e}")

    def update_text_color(self, new_color: str) -> None:
        """Update global text color and refresh styles."""
        self.app.app_config.text_color = new_color
        self.app.config_manager.update_app_setting("text_color", new_color)
        self.apply_theme(self.get_current_theme())

    def update_input_bg_color(self, new_color: str) -> None:
        """Update input background color and refresh styles."""
        self.app.app_config.custom_input_bg_color = new_color
        self.app.config_manager.update_app_setting("custom_input_bg_color", new_color)
        self.apply_theme(self.get_current_theme())

    def update_frame_transparency(self, transparent: bool) -> None:
        """Toggle frame transparency and refresh styles."""
        self.app.app_config.transparent_frames = transparent
        self.app.config_manager.update_app_setting("transparent_frames", transparent)
        self.apply_theme(self.get_current_theme())

    def refresh_global_shadows(self) -> None:
        """Refresh shadow effects on all applicable widgets."""
        # TODO: Implement shadow application logic
        pass