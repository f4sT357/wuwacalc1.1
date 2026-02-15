"""
Display Settings Dialog Module (PySide6)

Handles visual customization settings including base themes 
and element-based accent coloring.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QComboBox, QCheckBox, QMessageBox, QColorDialog, QRadioButton, 
    QButtonGroup, QGroupBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFontDatabase

if TYPE_CHECKING:
    from wuwacalc17 import ScoreCalculatorApp


class DisplaySettingsDialog(QDialog):
    """Visual settings dialog focused on themes and accent colors."""

    def __init__(self, parent: ScoreCalculatorApp):
        super().__init__(parent)
        self.app = parent
        self.setWindowTitle(self.app.tr("display_settings"))
        self.setMinimumSize(450, 350)

        # Local state mirroring config
        config = self.app.app_config
        self.selected_theme = config.theme
        self.selected_accent_mode = getattr(config, "accent_mode", "auto")
        self.selected_custom_accent = getattr(config, "custom_accent_color", "#FFD700")
        self.selected_font = config.app_font
        self.selected_transparency = config.transparent_frames

        self.init_ui()

    def init_ui(self) -> None:
        """Initialize the UI components."""
        layout = QVBoxLayout(self)

        # 1. Base Theme (Dark / Light only)
        base_group = QGroupBox(self.app.tr("base_theme_settings", "ベーステーマ"))
        base_layout = QHBoxLayout(base_group)
        self.rb_dark = QRadioButton(self.app.tr("dark_theme"))
        self.rb_light = QRadioButton(self.app.tr("light_theme"))
        self.base_theme_group = QButtonGroup(self)
        self.base_theme_group.addButton(self.rb_dark)
        self.base_theme_group.addButton(self.rb_light)
        
        if self.selected_theme == "light":
            self.rb_light.setChecked(True)
        else:
            self.rb_dark.setChecked(True)
            
        base_layout.addWidget(self.rb_dark)
        base_layout.addWidget(self.rb_light)
        layout.addWidget(base_group)

        # 2. Accent Coloring (Auto / Custom)
        accent_group = QGroupBox(self.app.tr("accent_coloring", "アクセント配色"))
        accent_layout = QVBoxLayout(accent_group)
        
        mode_layout = QHBoxLayout()
        self.rb_acc_auto = QRadioButton(self.app.tr("accent_auto", "オート (キャラ属性連動)"))
        self.rb_acc_custom = QRadioButton(self.app.tr("accent_custom", "カスタム"))
        self.accent_mode_group = QButtonGroup(self)
        self.accent_mode_group.addButton(self.rb_acc_auto)
        self.accent_mode_group.addButton(self.rb_acc_custom)
        
        if self.selected_accent_mode == "custom":
            self.rb_acc_custom.setChecked(True)
        else:
            self.rb_acc_auto.setChecked(True)
            
        mode_layout.addWidget(self.rb_acc_auto)
        mode_layout.addWidget(self.rb_acc_custom)
        accent_layout.addLayout(mode_layout)

        # Custom Color Picker
        custom_color_layout = QHBoxLayout()
        custom_color_layout.addWidget(QLabel(self.app.tr("custom_accent_color", "カスタムアクセント色")))
        self.btn_pick_accent = QPushButton(self.app.tr("select_color"))
        self.btn_pick_accent.clicked.connect(self._pick_custom_accent)
        custom_color_layout.addWidget(self.btn_pick_accent)
        self.lbl_accent_preview = QLabel()
        self.lbl_accent_preview.setFixedSize(50, 20)
        self._update_preview(self.lbl_accent_preview, self.selected_custom_accent)
        custom_color_layout.addWidget(self.lbl_accent_preview)
        accent_layout.addLayout(custom_color_layout)
        
        self.rb_acc_auto.toggled.connect(lambda: self.btn_pick_accent.setEnabled(False))
        self.rb_acc_custom.toggled.connect(lambda: self.btn_pick_accent.setEnabled(True))
        self.btn_pick_accent.setEnabled(self.selected_accent_mode == "custom")
        layout.addWidget(accent_group)

        # 3. Other Settings (Font, Transparency)
        misc_group = QGroupBox(self.app.tr("other_visual_settings", "その他の表示設定"))
        misc_layout = QVBoxLayout(misc_group)

        # Font
        font_layout = QHBoxLayout()
        font_layout.addWidget(QLabel(self.app.tr("font_settings")))
        self.combo_font = QComboBox()
        self.combo_font.addItem(self.app.tr("default_font"))
        fonts = self._get_compatible_fonts()
        self.combo_font.addItems(fonts)
        if self.selected_font in fonts:
            self.combo_font.setCurrentText(self.selected_font)
        font_layout.addWidget(self.combo_font)
        misc_layout.addLayout(font_layout)

        # Transparency
        self.cb_trans = QCheckBox(self.app.tr("transparent_frames"))
        self.cb_trans.setChecked(self.selected_transparency)
        misc_layout.addWidget(self.cb_trans)

        layout.addWidget(misc_group)

        # Action Buttons
        btn_box = QHBoxLayout()
        btn_apply = QPushButton(self.app.tr("apply"))
        btn_apply.clicked.connect(self._apply_settings)
        btn_reset = QPushButton(self.app.tr("full_reset"))
        btn_reset.clicked.connect(self._full_reset)
        btn_box.addStretch()
        btn_box.addWidget(btn_reset)
        btn_box.addWidget(btn_apply)
        layout.addLayout(btn_box)

    def _update_preview(self, lbl: QLabel, color: str) -> None:
        lbl.setStyleSheet(f"background-color: {color}; border: 1px solid gray;")

    def _pick_custom_accent(self) -> None:
        color = QColorDialog.getColor(QColor(self.selected_custom_accent), self)
        if color.isValid():
            self.selected_custom_accent = color.name()
            self._update_preview(self.lbl_accent_preview, self.selected_custom_accent)

    def _apply_settings(self) -> None:
        """Save settings and apply theme."""
        config = self.app.app_config
        config.theme = "light" if self.rb_light.isChecked() else "dark"
        config.accent_mode = "custom" if self.rb_acc_custom.isChecked() else "auto"
        config.custom_accent_color = self.selected_custom_accent
        config.app_font = "" if self.combo_font.currentIndex() == 0 else self.combo_font.currentText()
        config.transparent_frames = self.cb_trans.isChecked()
        
        self.app.apply_theme(config.theme)
        self.app.refresh_results_display()
        self.accept()

    def _full_reset(self) -> None:
        if QMessageBox.question(self, self.app.tr("full_reset"), 
                                self.app.tr("confirm_full_reset")) == QMessageBox.Yes:
            self.rb_dark.setChecked(True)
            self.rb_acc_auto.setChecked(True)
            self.combo_font.setCurrentIndex(0)
            self.cb_trans.setChecked(False)
            self._apply_settings()

    def _get_compatible_fonts(self) -> List[str]:
        db = QFontDatabase()
        compatible = [f for f in db.families() if QFontDatabase.WritingSystem.Japanese in db.writingSystems(f)]
        return sorted(compatible)