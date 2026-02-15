"""
UI Components Module (PySide6)
"""

from typing import Any, List, Tuple, Dict
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QGroupBox,
    QTextEdit,
    QSplitter,
    QComboBox,
    QCheckBox,
    QRadioButton,
    QSlider,
    QMenu,
    QLineEdit,
    QGridLayout,
    QButtonGroup,
    QTabWidget,
)
from PySide6.QtGui import QPixmap, QPainter, QPen, QColor
from PySide6.QtCore import Qt, Signal, QRect

from ui.ui_constants import (
    WINDOW_WIDTH,
    IMAGE_PREVIEW_MAX_HEIGHT,
)
from core.data_contracts import OCRResult

# Internal UI Constants
VALUE_ENTRY_WIDTH = 60

class OCRImageLabel(QLabel):
    """Custom label for drawing OCR bounding boxes and handling drag selection and file drops."""
    selection_completed = Signal(tuple)
    files_dropped = Signal(list)
    box_clicked = Signal(str, int) # ("main"|"sub", index/key)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ocr_result = None
        self.original_crop_size = None # (width, height)
        self.scale_factor = 1.0
        self.offset_x = 0
        self.offset_y = 0
        
        # Drag selection state
        self.start_pos = None
        self.end_pos = None
        self.is_selecting = False
        self.drag_enabled = True # Can be toggled
        self.crop_preview_rect = None # (l, t, w, h) in percent
        self.last_selection_pct = None # (l, t, r, b) in 0.0-1.0

        self.setText("No Image")
        # Enable mouse tracking if needed for hover, but drag works with press/move
        self.setMouseTracking(True)
        self.setAcceptDrops(True)

    def set_ocr_result(self, result, original_size=None):
        self.ocr_result = result
        if original_size:
            self.original_crop_size = original_size
        self.update()

    def set_drag_enabled(self, enabled: bool):
        self.drag_enabled = enabled
        if not enabled:
            self.start_pos = None
            self.end_pos = None
            self.is_selecting = False
            self.update()

    def set_crop_preview(self, l: float, t: float, w: float, h: float):
        """Set the crop preview rectangle in percentage (0-100)."""
        self.crop_preview_rect = (l, t, w, h)
        self.update()

    def mousePressEvent(self, event):
        if self.drag_enabled and self.pixmap():
            self.start_pos = event.position().toPoint()
            self.end_pos = self.start_pos
            self.is_selecting = True
            self.update()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.is_selecting and self.drag_enabled:
            self.end_pos = event.position().toPoint()
            self.update()
        elif self.ocr_result and self.pixmap():
            self._handle_hover(event.position().toPoint())
            super().mouseMoveEvent(event)
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.is_selecting and self.drag_enabled and self.pixmap():
            self.end_pos = event.position().toPoint()
            self.is_selecting = False
            self.update()
            
            # Calculate selection relative to the pixmap
            pix_size = self.pixmap().size()
            lbl_size = self.size()
            
            offset_x = (lbl_size.width() - pix_size.width()) // 2
            offset_y = (lbl_size.height() - pix_size.height()) // 2
            
            x1 = self.start_pos.x() - offset_x
            y1 = self.start_pos.y() - offset_y
            x2 = self.end_pos.x() - offset_x
            y2 = self.end_pos.y() - offset_y
            
            # Clamp to pixmap area
            x1 = max(0, min(pix_size.width(), x1))
            y1 = max(0, min(pix_size.height(), y1))
            x2 = max(0, min(pix_size.width(), x2))
            y2 = max(0, min(pix_size.height(), y2))
            
            if abs(x2 - x1) > 5 and abs(y2 - y1) > 5:
                # Normalize 0.0-1.0
                l = min(x1, x2) / pix_size.width()
                t = min(y1, y2) / pix_size.height()
                r = max(x1, x2) / pix_size.width()
                b = max(y1, y2) / pix_size.height()
                self.last_selection_pct = (l, t, r, b)
                self.selection_completed.emit(self.last_selection_pct)
        elif self.ocr_result and self.pixmap():
            # Check for click on OCR box
            match = self._find_box_at(event.position().toPoint())
            if match:
                typeinfo, idx_or_key, _ = match
                self.box_clicked.emit(typeinfo, idx_or_key)
            super().mouseReleaseEvent(event)
        else:
            super().mouseReleaseEvent(event)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            # Check if any URL is a local image file
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    local_path = url.toLocalFile().lower()
                    if local_path.endswith((".png", ".jpg", ".jpeg", ".bmp", ".gif")):
                        event.acceptProposedAction()
                        return
        super().dragEnterEvent(event)

    def dropEvent(self, event):
        paths = []
        for url in event.mimeData().urls():
            if url.isLocalFile():
                local_path = url.toLocalFile()
                if local_path.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".gif")):
                    paths.append(local_path)
        
        if paths:
            self.files_dropped.emit(paths)
            event.acceptProposedAction()
        else:
            super().dropEvent(event)

        if not self.pixmap():
            return

        painter = QPainter(self)
        
        pix_size = self.pixmap().size()
        lbl_size = self.size()
        self.offset_x = (lbl_size.width() - pix_size.width()) // 2
        self.offset_y = (lbl_size.height() - pix_size.height()) // 2

        # 1. Draw Mask / Selection / Preview
        if self.is_selecting and self.start_pos and self.end_pos:
            pen = QPen(QColor(255, 0, 0), 2, Qt.DashLine)
            painter.setPen(pen)
            rect = QRect(self.start_pos, self.end_pos).normalized()
            painter.drawRect(rect)
        elif self.crop_preview_rect:
            l, t, w, h = self.crop_preview_rect
            px_l = int(l * pix_size.width() / 100.0) + self.offset_x
            px_t = int(t * pix_size.height() / 100.0) + self.offset_y
            px_w = int(w * pix_size.width() / 100.0)
            px_h = int(h * pix_size.height() / 100.0)
            
            crop_rect = QRect(px_l, px_t, px_w, px_h)
            
            # Draw semi-transparent mask outside crop area
            painter.setBrush(QColor(0, 0, 0, 100))
            painter.setPen(Qt.NoPen)
            
            # Top mask
            painter.drawRect(self.offset_x, self.offset_y, pix_size.width(), px_t - self.offset_y)
            # Bottom mask
            painter.drawRect(self.offset_x, px_t + px_h, pix_size.width(), self.offset_y + pix_size.height() - (px_t + px_h))
            # Left mask
            painter.drawRect(self.offset_x, px_t, px_l - self.offset_x, px_h)
            # Right mask
            painter.drawRect(px_l + px_w, px_t, self.offset_x + pix_size.width() - (px_l + px_w), px_h)
            
            # Draw crop border
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(QColor(255, 50, 50), 2))
            painter.drawRect(crop_rect)

        if not self.ocr_result:
            return
        
        # Calculate scale factor
        if self.original_crop_size:
            # We assume the pixmap is scaled maintaining aspect ratio
            self.scale_factor = pix_size.width() / self.original_crop_size[0]
        else:
            self.scale_factor = 1.0
        
        # Draw Main Stat / Cost boxes
        pen_main = QPen(QColor(0, 255, 0, 180), 2)
        painter.setPen(pen_main)
        for key in ["main_stat", "cost"]:
            box = self.ocr_result.boxes.get(key)
            if box:
                self._draw_box(painter, box)

        # Draw Substat boxes
        pen_sub = QPen(QColor(0, 120, 255, 180), 2)
        painter.setPen(pen_sub)
        for sub in self.ocr_result.substats:
            if sub.box:
                self._draw_box(painter, sub.box)

    def _draw_box(self, painter, box, color=None):
        x, y, w, h = box
        if color:
            painter.setPen(QPen(color, 2))
        painter.drawRect(
            int(x * self.scale_factor + self.offset_x),
            int(y * self.scale_factor + self.offset_y),
            int(w * self.scale_factor),
            int(h * self.scale_factor)
        )

    def _find_box_at(self, pos):
        if not self.ocr_result: return None
        # Reverse scaling/offsets
        target_x = (pos.x() - self.offset_x) / self.scale_factor
        target_y = (pos.y() - self.offset_y) / self.scale_factor
        # Check main/cost
        for key, box in self.ocr_result.boxes.items():
            x, y, w, h = box
            if x <= target_x <= x + w and y <= target_y <= y + h:
                return ("main", key, box)
        # Check substats
        for i, sub in enumerate(self.ocr_result.substats):
            if sub.box:
                x, y, w, h = sub.box
                if x <= target_x <= x + w and y <= target_y <= y + h:
                    return ("sub", i, sub)
        return None

    def _handle_hover(self, pos):
        from PySide6.QtWidgets import QToolTip
        match = self._find_box_at(pos)
        if match:
            typeinfo, key_idx, obj = match
            if typeinfo == "main":
                text = f"{key_idx.replace('_', ' ').title()}"
            else:
                text = f"{obj.stat_name}: {obj.value}"
            QToolTip.showText(self.mapToGlobal(pos), text, self)
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            QToolTip.hideText()
            self.setCursor(Qt.CursorShape.ArrowCursor)


class UIComponents:
    def __init__(self, app: "ScoreCalculatorApp") -> None:
        self.app = app
        self.action_buttons = {}

        # Pre-initialize core widgets
        self.config_combo = QComboBox()
        self.character_combo = QComboBox()
        self.lang_combo = QComboBox()

        self.character_combo.setEditable(True)
        self.character_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        if self.character_combo.completer():
            self.character_combo.completer().setFilterMode(Qt.MatchFlag.MatchContains)

        self.rb_manual = QRadioButton()
        self.rb_ocr = QRadioButton()
        self.cb_auto_main = QCheckBox()
        self.rb_batch = QRadioButton()
        self.rb_single = QRadioButton()

        self.method_checkboxes: Dict[str, QCheckBox] = {
            "normalized": QCheckBox(),
            "ratio": QCheckBox(),
            "roll": QCheckBox(),
            "effective": QCheckBox(),
            "cv": QCheckBox(),
        }

        # Attribute holders for labels and other widgets that need retranslation
        self.lbl_cost_config = QLabel()
        self.lbl_character = QLabel()
        self.lbl_language = QLabel()
        self.lbl_input_mode = QLabel()
        self.lbl_calc_mode = QLabel()
        self.lbl_methods = QLabel()

        self.btn_load = QPushButton()
        self.btn_paste = QPushButton()
        self.btn_crop = QPushButton()
        self.btn_apply_crop = QPushButton()
        self.cb_auto_calculate = QCheckBox()
        self.lbl_crop_mode = QLabel()
        self.rb_crop_drag = QRadioButton()
        self.rb_crop_percent = QRadioButton()

        self.crop_labels: Dict[str, QLabel] = {}

        # Attribute holders for app-side reference
        self.main_widget = None
        self.settings_group = None
        self.image_group = None
        self.result_group = None
        self.log_group = None

    def create_main_layout(self) -> None:
        self.main_widget = QWidget()
        layout = QVBoxLayout(self.main_widget)
        layout.setContentsMargins(2, 2, 2, 2)

        self.main_tabs = QTabWidget()
        layout.addWidget(self.main_tabs)

        # 1. Calculator Tab
        calc_tab = QWidget()
        calc_layout = QVBoxLayout(calc_tab)
        self._setup_calculator_tab(calc_layout)
        self.main_tabs.addTab(calc_tab, self.app.tr("calculator") if hasattr(self.app, "tr") else "Calculator")

        # 2. Settings Tab
        settings_tab = QWidget()
        settings_layout = QVBoxLayout(settings_tab)
        self._setup_settings_tab(settings_layout)
        self.main_tabs.addTab(settings_tab, self.app.tr("settings") if hasattr(self.app, "tr") else "Settings")

        # 3. Log Tab
        log_tab = QWidget()
        log_layout = QVBoxLayout(log_tab)
        self._setup_log_tab(log_layout)
        self.main_tabs.addTab(log_tab, self.app.tr("log") if hasattr(self.app, "tr") else "Log")

    def _setup_calculator_tab(self, layout: QVBoxLayout) -> None:
        # Top Bar: Character, Config, Calculate
        top_h = QHBoxLayout()
        
        self.lbl_character.setText(self.app.tr("character"))
        top_h.addWidget(self.lbl_character)
        top_h.addWidget(self.character_combo, 1)

        self.lbl_cost_config.setText(self.app.tr("cost_config"))
        top_h.addWidget(self.lbl_cost_config)
        self.config_combo.clear() # Clear it as it's populated in setup_settings_ui normally
        self.config_combo.addItems(list(self.app.data_manager.tab_configs.keys()))
        self.config_combo.setCurrentText(self.app.current_config_key)
        top_h.addWidget(self.config_combo, 1)

        btn_calc = QPushButton(self.app.tr("calculate"))
        btn_calc.setObjectName("btn_main_calculate")
        btn_calc.clicked.connect(self.app.events.trigger_calculation)
        btn_calc.setMinimumHeight(40)
        btn_calc.setStyleSheet("font-weight: bold; font-size: 14px;")
        top_h.addWidget(btn_calc, 1)
        
        layout.addLayout(top_h)

        # Main Area: Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        # Left: Echo Tabs & Results
        left_w = QWidget()
        left_l = QVBoxLayout(left_w)
        left_l.setContentsMargins(0, 5, 0, 0)
        
        # Add notebook
        left_l.addWidget(self.app.notebook, 2)
        
        # Results area
        self.result_group = QGroupBox(self.app.tr("calc_result"))
        res_l = QVBoxLayout(self.result_group)
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        res_l.addWidget(self.result_text)
        left_l.addWidget(self.result_group, 3)
        
        splitter.addWidget(left_w)

        # Right: Image Preview & Control
        right_w = QWidget()
        right_l = QVBoxLayout(right_w)
        right_l.setContentsMargins(0, 5, 0, 0)

        # Image Groupbox
        self.image_group = QGroupBox(self.app.tr("ocr_image"))
        img_vbox = QVBoxLayout(self.image_group)
        
        # Image Control Buttons
        btn_h = QHBoxLayout()
        self.btn_load.setText(self.app.tr("load_image"))
        self.btn_load.clicked.connect(self.app.events.import_image)
        btn_h.addWidget(self.btn_load)

        self.btn_paste.setText(self.app.tr("paste_clipboard"))
        self.btn_paste.clicked.connect(self.app.events.paste_from_clipboard)
        btn_h.addWidget(self.btn_paste)

        self.btn_crop.setText(self.app.tr("perform_crop"))
        self.btn_crop.clicked.connect(self.app.image_proc.perform_crop)
        btn_h.addWidget(self.btn_crop)

        self.btn_apply_crop.setText(self.app.tr("apply_selection"))
        self.btn_apply_crop.clicked.connect(self.app.events.apply_selection_to_crop)
        self.btn_apply_crop.setVisible(False) # Hide by default, show in drag mode
        btn_h.addWidget(self.btn_apply_crop)
        
        img_vbox.addLayout(btn_h)

        self.image_label = OCRImageLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumHeight(IMAGE_PREVIEW_MAX_HEIGHT)
        self.image_label.set_drag_enabled(self.app.crop_mode_var == "drag")
        img_vbox.addWidget(self.image_label)
        
        right_l.addWidget(self.image_group)

        # Extra Actions Group
        act_group = QGroupBox(self.app.tr("actions"))
        act_l = QGridLayout(act_group)
        
        # Row 1
        self.btn_equip = QPushButton(self.app.tr("set_equipped"))
        self.btn_equip.clicked.connect(self.app.set_current_as_equipped)
        act_l.addWidget(self.btn_equip, 0, 0)

        self.btn_score = QPushButton(self.app.tr("scoreboard"))
        self.btn_score.clicked.connect(self.app.events.generate_scoreboard)
        act_l.addWidget(self.btn_score, 0, 1)

        # Row 2
        self.btn_export = QPushButton(self.app.tr("export_txt"))
        self.btn_export.clicked.connect(self.app.export_result_to_txt)
        act_l.addWidget(self.btn_export, 1, 0)

        self.btn_clear = QPushButton(self.app.tr("clear_all"))
        self.btn_clear.clicked.connect(self.app.clear_all)
        act_l.addWidget(self.btn_clear, 1, 1)

        right_l.addWidget(act_group)
        
        splitter.addWidget(right_w)
        splitter.setSizes([WINDOW_WIDTH // 2, WINDOW_WIDTH // 2])

    def _setup_settings_tab(self, layout: QVBoxLayout) -> None:
        # 1. General & Language
        self.gen_group = QGroupBox(self.app.tr("general_settings"))
        gen_grid = QGridLayout(self.gen_group)
        
        gen_grid.addWidget(self.lbl_language, 0, 0)
        self.lang_combo.clear()
        self.lang_combo.addItems(["ja", "en", "zh-CN"])
        self.lang_combo.setCurrentText(self.app.language)
        gen_grid.addWidget(self.lang_combo, 0, 1)

        self.cb_auto_main.setText(self.app.tr("auto_main"))
        self.cb_auto_main.setChecked(self.app.auto_apply_main_stats)
        gen_grid.addWidget(self.cb_auto_main, 1, 0, 1, 2)

        self.cb_auto_calculate.setText(self.app.tr("auto_calculate"))
        self.cb_auto_calculate.setChecked(self.app.app_config.auto_calculate)
        gen_grid.addWidget(self.cb_auto_calculate, 2, 0, 1, 2)

        layout.addWidget(self.gen_group)

        # 2. Calculation Methods
        self.calc_group = QGroupBox(self.app.tr("calculation_settings"))
        calc_vbox = QVBoxLayout(self.calc_group)
        
        # Calc Mode (Batch vs Single)
        mode_h = QHBoxLayout()
        self.lbl_calc_mode.setText(self.app.tr("calc_mode"))
        mode_h.addWidget(self.lbl_calc_mode)
        self.rb_batch.setText(self.app.tr("batch"))
        self.rb_single.setText(self.app.tr("single_only"))
        
        self.grp_calc_mode = QButtonGroup(self.main_widget)
        self.grp_calc_mode.addButton(self.rb_batch)
        self.grp_calc_mode.addButton(self.rb_single)
        
        if self.app.score_mode_var == "batch":
            self.rb_batch.setChecked(True)
        else:
            self.rb_single.setChecked(True)
        mode_h.addWidget(self.rb_batch)
        mode_h.addWidget(self.rb_single)
        calc_vbox.addLayout(mode_h)

        # Methods Checkboxes
        methods_h = QHBoxLayout()
        self.lbl_methods.setText(self.app.tr("methods_label"))
        methods_h.addWidget(self.lbl_methods)
        enabled = self.app.app_config.enabled_calc_methods
        for m, cb in self.method_checkboxes.items():
            cb.setText(self.app.tr(f"method_{m}"))
            cb.setChecked(enabled.get(m, True))
            methods_h.addWidget(cb)
        calc_vbox.addLayout(methods_h)
        
        layout.addWidget(self.calc_group)

        # 3. OCR & Crop Settings
        self.ocr_group = QGroupBox(self.app.tr("ocr_settings"))
        ocr_vbox = QVBoxLayout(self.ocr_group)

        # Input Mode
        input_h = QHBoxLayout()
        self.lbl_input_mode.setText(self.app.tr("input_mode"))
        input_h.addWidget(self.lbl_input_mode)
        self.rb_manual.setText(self.app.tr("manual"))
        self.rb_ocr.setText(self.app.tr("ocr"))
        
        self.grp_input_mode = QButtonGroup(self.main_widget)
        self.grp_input_mode.addButton(self.rb_manual)
        self.grp_input_mode.addButton(self.rb_ocr)
        
        if self.app.mode_var == "ocr":
            self.rb_ocr.setChecked(True)
        else:
            self.rb_manual.setChecked(True)
        input_h.addWidget(self.rb_manual)
        input_h.addWidget(self.rb_ocr)
        ocr_vbox.addLayout(input_h)

        # Crop Mode & Sliders
        crop_main_h = QHBoxLayout()
        self.lbl_crop_mode.setText(self.app.tr("crop_mode"))
        crop_main_h.addWidget(self.lbl_crop_mode)
        self.rb_crop_drag.setText(self.app.tr("drag"))
        self.rb_crop_percent.setText(self.app.tr("percent"))
        
        self.grp_crop_mode = QButtonGroup(self.main_widget)
        self.grp_crop_mode.addButton(self.rb_crop_drag)
        self.grp_crop_mode.addButton(self.rb_crop_percent)
        
        if self.app.crop_mode_var == "drag":
            self.rb_crop_drag.setChecked(True)
        else:
            self.rb_crop_percent.setChecked(True)
        crop_main_h.addWidget(self.rb_crop_drag)
        crop_main_h.addWidget(self.rb_crop_percent)
        ocr_vbox.addLayout(crop_main_h)

        crop_sliders_h = QHBoxLayout()
        self.entry_crop_l, self.slider_crop_l, lbl_l = self._create_crop_item(
            crop_sliders_h, self.app.tr("left_percent"), self.app.app_config.crop_left_percent, "slider_crop_l"
        )
        self.entry_crop_t, self.slider_crop_t, lbl_t = self._create_crop_item(
            crop_sliders_h, self.app.tr("top_percent"), self.app.app_config.crop_top_percent, "slider_crop_t"
        )
        self.entry_crop_w, self.slider_crop_w, lbl_w = self._create_crop_item(
            crop_sliders_h, self.app.tr("width_percent"), self.app.app_config.crop_width_percent, "slider_crop_w"
        )
        self.entry_crop_h, self.slider_crop_h, lbl_h = self._create_crop_item(
            crop_sliders_h, self.app.tr("height_percent"), self.app.app_config.crop_height_percent, "slider_crop_h"
        )
        self.crop_labels["L"] = lbl_l
        self.crop_labels["T"] = lbl_t
        self.crop_labels["W"] = lbl_w
        self.crop_labels["H"] = lbl_h
        ocr_vbox.addLayout(crop_sliders_h)

        layout.addWidget(self.ocr_group)

        # 4. Dialog Buttons
        diag_h = QHBoxLayout()
        
        self.btn_char_set = QPushButton(self.app.tr("char_setting"))
        self.menu_char_set = QMenu(self.btn_char_set)
        self.act_char_new = self.menu_char_set.addAction(self.app.tr("new"))
        self.act_char_new.triggered.connect(self.app.events.open_char_settings_new)
        self.act_char_edit = self.menu_char_set.addAction(self.app.tr("edit"))
        self.act_char_edit.triggered.connect(self.app.events.open_char_settings_edit)
        self.btn_char_set.setMenu(self.menu_char_set)
        diag_h.addWidget(self.btn_char_set)

        self.btn_hist = QPushButton(self.app.tr("history"))
        self.btn_hist.clicked.connect(self.app.events.open_history)
        diag_h.addWidget(self.btn_hist)

        self.btn_disp = QPushButton(self.app.tr("display_settings"))
        self.btn_disp.clicked.connect(self.app.events.open_display_settings)
        diag_h.addWidget(self.btn_disp)

        self.btn_pre = QPushButton(self.app.tr("preprocess_settings"))
        self.btn_pre.clicked.connect(self.app.events.open_image_preprocessing_settings)
        diag_h.addWidget(self.btn_pre)

        self.btn_help = QPushButton(self.app.tr("help"))
        self.btn_help.clicked.connect(self.app._open_readme)
        diag_h.addWidget(self.btn_help)

        layout.addLayout(diag_h)
        layout.addStretch()

    def _setup_log_tab(self, layout: QVBoxLayout) -> None:
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)

    def _create_crop_item(
        self, layout: QHBoxLayout, label_text: str, val: float, name: str
    ) -> Tuple[QLineEdit, QSlider, QLabel]:
        vbox = QVBoxLayout()
        lbl = QLabel(label_text)
        vbox.addWidget(lbl)
        e = QLineEdit(str(val))
        e.setFixedWidth(40)
        e.textChanged.connect(self.app.events.on_crop_percent_change)
        vbox.addWidget(e)
        s = QSlider(Qt.Orientation.Horizontal)
        s.setRange(0, 100)
        s.setValue(int(val))
        s.setObjectName(name)
        s.valueChanged.connect(self.app.events.on_crop_slider_change)
        vbox.addWidget(s)
        layout.addLayout(vbox)
        return e, s, lbl

    def retranslate_ui(self) -> None:
        # Tab names
        self.main_tabs.setTabText(0, self.app.tr("calculator"))
        self.main_tabs.setTabText(1, self.app.tr("settings"))
        self.main_tabs.setTabText(2, self.app.tr("log"))

        # Calculator Tab
        self.lbl_character.setText(self.app.tr("character"))
        self.lbl_cost_config.setText(self.app.tr("cost_config"))
        # Find the calculate button by object name if not stored
        btn_calc = self.main_tabs.widget(0).findChild(QPushButton, "btn_main_calculate")
        if btn_calc:
            btn_calc.setText(self.app.tr("calculate"))

        self.result_group.setTitle(self.app.tr("calc_result"))
        self.image_group.setTitle(self.app.tr("ocr_image"))
        self.btn_load.setText(self.app.tr("load_image"))
        self.btn_load.setToolTip(self.app.tr("tooltip_load_image"))
        self.btn_paste.setText(self.app.tr("paste_clipboard"))
        self.btn_paste.setToolTip(self.app.tr("tooltip_paste"))
        self.btn_crop.setText(self.app.tr("perform_crop"))
        self.btn_crop.setToolTip(self.app.tr("tooltip_crop"))
        self.btn_apply_crop.setText(self.app.tr("apply_selection"))
        self.btn_apply_crop.setToolTip(self.app.tr("tooltip_apply_selection"))

        self.btn_equip.setText(self.app.tr("set_equipped"))
        self.btn_score.setText(self.app.tr("scoreboard"))
        self.btn_export.setText(self.app.tr("export_txt"))
        self.btn_clear.setText(self.app.tr("clear_all"))

        # Settings Tab
        # (Assuming these labels/combos are stored as self.attributes)
        self.lbl_language.setText(self.app.tr("language"))
        self.lbl_input_mode.setText(self.app.tr("input_mode"))
        self.rb_manual.setText(self.app.tr("manual"))
        self.rb_ocr.setText(self.app.tr("ocr"))
        self.rb_manual.setToolTip(self.app.tr("tooltip_manual_mode"))
        self.rb_ocr.setToolTip(self.app.tr("tooltip_ocr_mode"))
        self.cb_auto_main.setText(self.app.tr("auto_main"))
        self.cb_auto_calculate.setText(self.app.tr("auto_calculate"))
        self.cb_auto_calculate.setToolTip(self.app.tr("tooltip_auto_calculate"))

        self.lbl_calc_mode.setText(self.app.tr("calc_mode"))
        self.rb_batch.setText(self.app.tr("batch"))
        self.rb_single.setText(self.app.tr("single_only"))
        self.rb_batch.setToolTip(self.app.tr("tooltip_batch_mode"))
        self.rb_single.setToolTip(self.app.tr("tooltip_single_mode"))

        self.lbl_methods.setText(self.app.tr("methods_label"))
        for m, cb in self.method_checkboxes.items():
            cb.setText(self.app.tr(f"method_{m}"))

        self.lbl_crop_mode.setText(self.app.tr("crop_mode"))
        self.rb_crop_drag.setText(self.app.tr("drag"))
        self.rb_crop_percent.setText(self.app.tr("percent"))

        self.crop_labels["L"].setText(self.app.tr("left_percent"))
        self.crop_labels["T"].setText(self.app.tr("top_percent"))
        self.crop_labels["W"].setText(self.app.tr("width_percent"))
        self.crop_labels["H"].setText(self.app.tr("height_percent"))

        # Missing Settings groups and buttons
        if hasattr(self, "gen_group"): self.gen_group.setTitle(self.app.tr("general_settings"))
        if hasattr(self, "calc_group"): self.calc_group.setTitle(self.app.tr("calculation_settings"))
        if hasattr(self, "ocr_group"): self.ocr_group.setTitle(self.app.tr("ocr_settings"))
        
        if hasattr(self, "btn_char_set"): 
            self.btn_char_set.setText(self.app.tr("char_setting"))
            if hasattr(self, "act_char_new"): self.act_char_new.setText(self.app.tr("new"))
            if hasattr(self, "act_char_edit"): self.act_char_edit.setText(self.app.tr("edit"))
            
        if hasattr(self, "btn_hist"): self.btn_hist.setText(self.app.tr("history"))
        if hasattr(self, "btn_disp"): self.btn_disp.setText(self.app.tr("display_settings"))
        if hasattr(self, "btn_pre"): self.btn_pre.setText(self.app.tr("preprocess_settings"))
        if hasattr(self, "btn_help"): self.btn_help.setText(self.app.tr("help"))
        if hasattr(self, "btn_apply_crop"):
            self.btn_apply_crop.setText(self.app.tr("apply_selection"))
            self.btn_apply_crop.setToolTip(self.app.tr("tooltip_apply_selection"))

        # Update character combo first item (placeholder)
        self.character_combo.setItemText(0, f"-- {self.app.tr('character')} --")

        if not self.app.image_proc.loaded_image:
            self.image_label.setText(self.app.tr("no_image"))

    def display_ocr_overlay(self, result: OCRResult) -> None:
        """Displays bounding boxes on the current image preview."""
        if hasattr(self, 'image_label') and isinstance(self.image_label, OCRImageLabel):
            if self.image_label.pixmap():
                # Get the size of the CROPPED image used for OCR
                orig_size = None
                if self.app.image_proc.loaded_image:
                    orig_size = self.app.image_proc.loaded_image.size
                self.image_label.set_ocr_result(result, original_size=orig_size)

    def update_ui_mode(self) -> None:
        is_ocr = self.app.mode_var == "ocr"
        is_p = self.app.crop_mode_var == "percent"
        for attr in [
            "entry_crop_l",
            "slider_crop_l",
            "entry_crop_t",
            "slider_crop_t",
            "entry_crop_w",
            "slider_crop_w",
            "entry_crop_h",
            "slider_crop_h",
        ]:
            if hasattr(self, attr):
                getattr(self, attr).setVisible(is_ocr and is_p)

        if hasattr(self, "btn_apply_crop"):
            self.btn_apply_crop.setVisible(is_ocr and not is_p)
            
        # Initialize/refresh preview box
        if is_ocr and is_p:
            c = self.app.app_config
            self.image_label.set_crop_preview(
                c.crop_left_percent, c.crop_top_percent, 
                c.crop_width_percent, c.crop_height_percent
            )
        else:
            self.image_label.set_crop_preview(0, 0, 0, 0)

    def filter_characters_by_config(self) -> None:
        key = getattr(self.app, "current_config_key", "")
        profiles = self.app.character_manager.get_character_list_by_config(key)
        if not profiles:
            profiles = self.app.character_manager.get_all_characters(self.app.language)
        self.update_character_combo(profiles, self.app.character_var)

    def update_character_combo(self, profiles: List[Any], current: str = "") -> None:
        self.character_combo.blockSignals(True)
        self.character_combo.clear()

        lang = self.app.language
        formatted = []
        for p in profiles:
            if isinstance(p, dict):
                jp = p.get("name_jp", "")
                en = p.get("name_en", "")
                display_name = en if lang == "en" else jp
                formatted.append((display_name, en))
            elif isinstance(p, tuple):
                # (display_name, internal_name)
                formatted.append(p)

        # Sort by display name
        formatted.sort(key=lambda x: x[0])

        self.character_combo.addItem(f"-- {self.app.tr('character')} --", userData="")
        for display_name, internal_name in formatted:
            self.character_combo.addItem(display_name, userData=internal_name)

        idx = self.character_combo.findData(current)
        if idx >= 0:
            self.character_combo.setCurrentIndex(idx)
        else:
            self.character_combo.setCurrentIndex(0)

        if self.character_combo.currentIndex() <= 0:
            self.character_combo.setEditText("")

        self.character_combo.blockSignals(False)
        self.app.logger.info(f"Populated character combo with {len(formatted)} items in {lang}.")
