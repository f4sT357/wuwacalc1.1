from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QRubberBand, QMessageBox
from PySide6.QtCore import Qt, QRect, QSize, QPoint
from PySide6.QtGui import QPixmap
from utils.constants import DIALOG_CROP_WIDTH, DIALOG_CROP_HEIGHT

try:
    from PIL import Image, ImageQt

    is_pil_installed = True
except ImportError:
    is_pil_installed = False


class CropLabel(QLabel):
    """QLabel with rubber band selection."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.rubberBand = QRubberBand(QRubberBand.Shape.Rectangle, self)
        self.origin = QPoint()
        self.current_rect = QRect()
        self.is_selecting = False

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.origin = event.pos()
            self.rubberBand.setGeometry(QRect(self.origin, QSize()))
            self.rubberBand.show()
            self.is_selecting = True

    def mouseMoveEvent(self, event):
        if self.is_selecting:
            self.rubberBand.setGeometry(QRect(self.origin, event.pos()).normalized())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_selecting = False
            self.current_rect = self.rubberBand.geometry()

    def get_selection(self):
        return self.current_rect


class CropDialog(QDialog):
    """Dialog for selecting and inputting image crop method (interactive)."""

    def __init__(self, parent, pil_image):
        super().__init__(parent)
        self.app = parent
        self.setWindowTitle(self.app.tr("crop_title"))
        self.resize(DIALOG_CROP_WIDTH, DIALOG_CROP_HEIGHT)
        self.crop_result = None
        self.pil_image = pil_image
        self.scale_ratio = 1.0
        self.percent_label = None
        self.confirm_checkbox = None
        self.last_percent = None
        self.init_ui()

    def init_ui(self):
        import os
        from PySide6.QtWidgets import QCheckBox, QComboBox, QLineEdit

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(self.app.tr("crop_instruction")))

        # 連携説明ラベルを追加
        sync_notice = QLabel(self.app.tr("crop_sync_notice"))
        sync_notice.setStyleSheet("color: #FFB300; font-size: 10px;")  # 目立つように少し色を変える
        sync_notice.setWordWrap(True)
        layout.addWidget(sync_notice)

        self.image_label = CropLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        # パーセント表示用ラベル
        self.percent_label = QLabel("")
        layout.addWidget(self.percent_label)

        # 適用確認用チェックボックス
        self.confirm_checkbox = QCheckBox(self.app.tr("crop_confirm_apply"))
        self.confirm_checkbox.setChecked(True)
        layout.addWidget(self.confirm_checkbox)

        # パーセントで適用するチェックボックス（%設定エリアを適用）
        self.percent_apply_checkbox = QCheckBox(self.app.tr("crop_apply_percent"))
        self.percent_apply_checkbox.setChecked(True)
        # ホバー時の説明（ツールチップ）
        self.percent_apply_checkbox.setToolTip(self.app.tr("crop_apply_percent_tooltip"))
        layout.addWidget(self.percent_apply_checkbox)

        # --- プリセットUI ---
        preset_layout = QHBoxLayout()
        self.preset_combo = QComboBox()
        self.preset_combo.setEditable(False)
        self.preset_combo.setMinimumWidth(120)
        self.preset_name_input = QLineEdit()
        self.preset_name_input.setPlaceholderText(self.app.tr("preset_name_placeholder"))
        self.preset_input = QLineEdit()
        self.preset_input.setPlaceholderText(self.app.tr("preset_placeholder_format"))
        btn_save = QPushButton(self.app.tr("save"))
        btn_load = QPushButton(self.app.tr("load"))
        btn_delete = QPushButton(self.app.tr("delete"))
        preset_layout.addWidget(self.preset_combo)
        preset_layout.addWidget(self.preset_name_input)
        preset_layout.addWidget(self.preset_input)
        preset_layout.addWidget(btn_save)
        preset_layout.addWidget(btn_load)
        preset_layout.addWidget(btn_delete)
        layout.addLayout(preset_layout)

        # この範囲をデフォルト設定として保存 用チェックボックス
        self.save_as_default_checkbox = QCheckBox(self.app.tr("crop_save_as_default"))
        self.save_as_default_checkbox.setChecked(False)
        # ホバー時の説明（ツールチップ）
        self.save_as_default_checkbox.setToolTip(self.app.tr("crop_save_as_default_tooltip"))
        layout.addWidget(self.save_as_default_checkbox)

        self._preset_file = os.path.join(os.path.dirname(__file__), "..", "crop_presets.json")
        self._load_presets()
        btn_save.clicked.connect(self._save_preset)
        btn_load.clicked.connect(self._apply_preset)
        btn_delete.clicked.connect(self._delete_preset)
        self.preset_combo.currentIndexChanged.connect(self._preset_combo_changed)

        # Load and display
        self._load_and_display_image()
        layout.addWidget(self.image_label)

        # CropLabelのマウスリリースでパーセント更新
        self.image_label.mouseReleaseEvent = self._wrap_mouse_release(self.image_label.mouseReleaseEvent)

        # もしデフォルトの切り取り範囲があれば読み込み表示する
        self._apply_current_app_crop_settings()

        # Buttons
        btn_layout = QHBoxLayout()
        btn_reset = QPushButton(self.app.tr("reset"))
        btn_reset.clicked.connect(self._reset_selection)

        btn_ok = QPushButton(self.app.tr("ok"))
        btn_ok.clicked.connect(self._ok)

        btn_cancel = QPushButton(self.app.tr("cancel"))
        btn_cancel.clicked.connect(self.reject)

        btn_layout.addWidget(btn_reset)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

    def _load_presets(self):
        import json
        import os

        self.presets = []
        try:
            preset_path = os.path.abspath(self._preset_file)
            if os.path.exists(preset_path):
                with open(preset_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.presets = data.get("crop_presets", [])
        except Exception:
            self.presets = []
        self.preset_combo.clear()
        for p in self.presets:
            self.preset_combo.addItem(p.get("name", f"{p['w']}x{p['h']}"))

    def _save_presets_to_file(self):
        import json
        import os

        try:
            preset_path = os.path.abspath(self._preset_file)
            with open(preset_path, "w", encoding="utf-8") as f:
                json.dump({"crop_presets": self.presets}, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _save_preset(self):
        text = self.preset_input.text().strip()
        name = self.preset_name_input.text().strip()
        if not name:
            QMessageBox.warning(self, self.app.tr("warning"), self.app.tr("preset_name_required"))
            return

        # If input is empty, use the current selection (last_percent)
        if not text and self.last_percent:
            l, t, w, h = self.last_percent
        else:
            try:
                # Support both comma and 'x' separators for flexibility
                import re

                vals = [float(v.strip().replace("%", "")) for v in re.split(r"[,x]", text)]

                if len(vals) == 4:
                    l, t, w, h = vals
                elif len(vals) == 2:
                    # Legacy 2D format: center it
                    w, h = vals
                    l = (100.0 - w) / 2
                    t = (100.0 - h) / 2
                else:
                    raise ValueError()
            except Exception:
                QMessageBox.warning(self, self.app.tr("warning"), self.app.tr("preset_format"))
                return

        self.presets.append({"name": name, "l": l, "t": t, "w": w, "h": h})
        self._save_presets_to_file()
        self._load_presets()

    def _apply_preset(self):
        idx = self.preset_combo.currentIndex()
        if idx < 0 or idx >= len(self.presets):
            return
        preset = self.presets[idx]

        # Extract 4D data with legacy fallback
        w, h = preset["w"], preset["h"]
        l = preset.get("l", (100.0 - w) / 2)
        t = preset.get("t", (100.0 - h) / 2)

        img_w, img_h = self.pil_image.size

        # Convert percentages to original pixels
        orig_l = int(img_w * l / 100.0)
        orig_t = int(img_h * t / 100.0)
        orig_w = int(img_w * w / 100.0)
        orig_h = int(img_h * h / 100.0)

        # Scale for display
        l_s = int(orig_l * self.scale_ratio)
        t_s = int(orig_t * self.scale_ratio)
        w_s = int(orig_w * self.scale_ratio)
        h_s = int(orig_h * self.scale_ratio)

        self.image_label.rubberBand.setGeometry(QRect(l_s, t_s, w_s, h_s))
        self.image_label.rubberBand.show()
        self.image_label.current_rect = QRect(l_s, t_s, w_s, h_s)
        self._update_percent_label()

    def _delete_preset(self):
        idx = self.preset_combo.currentIndex()
        if idx < 0 or idx >= len(self.presets):
            return
        del self.presets[idx]
        self._save_presets_to_file()
        self._load_presets()

    def _preset_combo_changed(self, idx):
        if idx < 0 or idx >= len(self.presets):
            return
        preset = self.presets[idx]

        # Get values with fallbacks for legacy presets
        w, h = preset["w"], preset["h"]
        l = preset.get("l", (100.0 - w) / 2)
        t = preset.get("t", (100.0 - h) / 2)

        self.preset_name_input.setText(preset["name"])
        self.preset_input.setText(f"{l:.1f},{t:.1f},{w:.1f},{h:.1f}")

    def _wrap_mouse_release(self, orig_func):
        def wrapped(event):
            orig_func(event)
            self._update_percent_label()

        return wrapped

    def _update_percent_label(self):
        rect = self.image_label.get_selection()
        if rect.isEmpty():
            self.percent_label.setText("")
            self.last_percent = None
            return

        img_w, img_h = self.pil_image.size

        # Calculate original coordinates (reversing display scale)
        orig_l = rect.x() / self.scale_ratio
        orig_t = rect.y() / self.scale_ratio
        orig_w = rect.width() / self.scale_ratio
        orig_h = rect.height() / self.scale_ratio

        # Convert to percentages
        p_l = orig_l / img_w * 100.0
        p_t = orig_t / img_h * 100.0
        p_w = orig_w / img_w * 100.0
        p_h = orig_h / img_h * 100.0

        self.last_percent = (p_l, p_t, p_w, p_h)
        self.percent_label.setText(f"L:{p_l:.1f}% T:{p_t:.1f}% W:{p_w:.1f}% H:{p_h:.1f}%")

        # Auto-update preset input field in L,T,W,H format
        if self.preset_input is not None:
            self.preset_input.setText(f"{p_l:.1f},{p_t:.1f},{p_w:.1f},{p_h:.1f}")

    def _load_and_display_image(self):
        if not self.pil_image or not is_pil_installed:
            return

        max_w, max_h = 850, 550
        w, h = self.pil_image.size

        scale_w = max_w / w
        scale_h = max_h / h
        self.scale_ratio = min(scale_w, scale_h, 1.0)

        new_w = int(w * self.scale_ratio)
        new_h = int(h * self.scale_ratio)

        # Ensure image is in a display-friendly mode and loaded
        if self.pil_image.mode != "RGBA" and self.pil_image.mode != "RGB":
            display_img = self.pil_image.convert("RGBA")
        else:
            display_img = self.pil_image

        resized = display_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        self.qim = ImageQt.ImageQt(resized)
        pixmap = QPixmap.fromImage(self.qim)

        self.image_label.setPixmap(pixmap)
        self.image_label.setFixedSize(new_w, new_h)

    def _apply_current_app_crop_settings(self):
        """Initialize the crop area from the main application's 4D percentage settings."""
        try:
            # Use current settings from the main app (L, T, W, H)
            left_p = float(self.app.crop_left_percent_var)
            top_p = float(self.app.crop_top_percent_var)
            width_p = float(self.app.crop_width_percent_var)
            height_p = float(self.app.crop_height_percent_var)

            img_w, img_h = self.pil_image.size

            # Convert percentages to original pixels
            orig_l = int(img_w * left_p / 100.0)
            orig_t = int(img_h * top_p / 100.0)
            orig_w = int(img_w * width_p / 100.0)
            orig_h = int(img_h * height_p / 100.0)

            # Convert to display scale
            l_s = int(orig_l * self.scale_ratio)
            t_s = int(orig_t * self.scale_ratio)
            w_s = int(orig_w * self.scale_ratio)
            h_s = int(orig_h * self.scale_ratio)

            self.image_label.rubberBand.setGeometry(QRect(l_s, t_s, w_s, h_s))
            self.image_label.rubberBand.show()
            self.image_label.current_rect = QRect(l_s, t_s, w_s, h_s)

            # Update labels and input fields
            self._update_percent_label()

        except Exception as e:
            # Fallback if values are invalid
            self.app.logger.debug(f"Failed to apply current crop settings to dialog: {e}")

    def _reset_selection(self):
        self.image_label.rubberBand.hide()
        self.image_label.current_rect = QRect()
        self._update_percent_label()

    def _ok(self):
        import json
        import os

        if self.confirm_checkbox and not self.confirm_checkbox.isChecked():
            QMessageBox.information(self, self.app.tr("info"), self.app.tr("crop_confirm_needed"))
            return

        rect = self.image_label.get_selection()

        # Helper to persist default crop (store as percentages)
        def _maybe_save_default(left_p, top_p, width_p, height_p):
            if not (self.save_as_default_checkbox and self.save_as_default_checkbox.isChecked()):
                return
            try:
                # 1. Update main application configuration
                self.app.config_manager.update_app_setting("crop_left_percent", float(left_p))
                self.app.config_manager.update_app_setting("crop_top_percent", float(top_p))
                self.app.config_manager.update_app_setting("crop_width_percent", float(width_p))
                self.app.config_manager.update_app_setting("crop_height_percent", float(height_p))

                # 2. Update application variables for immediate use
                self.app.crop_left_percent_var = float(left_p)
                self.app.crop_top_percent_var = float(top_p)
                self.app.crop_width_percent_var = float(width_p)
                self.app.crop_height_percent_var = float(height_p)

                # 3. Update main UI widgets (entries and sliders)
                # Disable signals temporarily to avoid redundant processing
                self.app.ui.entry_crop_l.blockSignals(True)
                self.app.ui.entry_crop_t.blockSignals(True)
                self.app.ui.entry_crop_w.blockSignals(True)
                self.app.ui.entry_crop_h.blockSignals(True)

                self.app.ui.entry_crop_l.setText(f"{left_p:.1f}")
                self.app.ui.entry_crop_t.setText(f"{top_p:.1f}")
                self.app.ui.entry_crop_w.setText(f"{width_p:.1f}")
                self.app.ui.entry_crop_h.setText(f"{height_p:.1f}")

                self.app.ui.slider_crop_l.setValue(int(left_p))
                self.app.ui.slider_crop_t.setValue(int(top_p))
                self.app.ui.slider_crop_w.setValue(int(width_p))
                self.app.ui.slider_crop_h.setValue(int(height_p))

                self.app.ui.entry_crop_l.blockSignals(False)
                self.app.ui.entry_crop_t.blockSignals(False)
                self.app.ui.entry_crop_w.blockSignals(False)
                self.app.ui.entry_crop_h.blockSignals(False)

                # 4. Save to config.json
                self.app.config_manager.save()

                # Also keep saving to crop_presets.json for dialog-specific defaults
                preset_path = os.path.abspath(self._preset_file)
                data = {}
                if os.path.exists(preset_path):
                    with open(preset_path, "r", encoding="utf-8") as f:
                        try:
                            data = json.load(f)
                        except Exception:
                            data = {}
                data["default_crop"] = {
                    "left_p": float(left_p),
                    "top_p": float(top_p),
                    "width_p": float(width_p),
                    "height_p": float(height_p),
                }
                with open(preset_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            except Exception:
                # Fail silently; not critical
                pass

        if rect.isEmpty():
            # Entire image
            if self.percent_apply_checkbox and self.percent_apply_checkbox.isChecked():
                left_p, top_p, width_p, height_p = 0.0, 0.0, 100.0, 100.0
                self.crop_result = ("percent", left_p, top_p, width_p, height_p)
                _maybe_save_default(left_p, top_p, width_p, height_p)
            else:
                self.crop_result = ("coords", 0, 0, self.pil_image.size[0], self.pil_image.size[1])
            self.accept()
            return

        # Convert coords (from displayed scaled image back to original image coords)
        x1 = rect.x()
        y1 = rect.y()
        x2 = rect.right()
        y2 = rect.bottom()

        orig_left = int(x1 / self.scale_ratio)
        orig_top = int(y1 / self.scale_ratio)
        orig_right = int(x2 / self.scale_ratio)
        orig_bottom = int(y2 / self.scale_ratio)

        # Limit to image bounds
        orig_left = max(0, orig_left)
        orig_top = max(0, orig_top)
        orig_right = min(self.pil_image.size[0], orig_right)
        orig_bottom = min(self.pil_image.size[1], orig_bottom)

        if (orig_right - orig_left) < 5 or (orig_bottom - orig_top) < 5:
            QMessageBox.warning(self, self.app.tr("warning"), self.app.tr("crop_too_small"))
            return

        if self.percent_apply_checkbox and self.percent_apply_checkbox.isChecked():
            img_w, img_h = self.pil_image.size
            left_p = orig_left / img_w * 100.0
            top_p = orig_top / img_h * 100.0
            width_p = (orig_right - orig_left) / img_w * 100.0
            height_p = (orig_bottom - orig_top) / img_h * 100.0
            self.crop_result = ("percent", left_p, top_p, width_p, height_p)
            _maybe_save_default(left_p, top_p, width_p, height_p)
        else:
            self.crop_result = ("coords", orig_left, orig_top, orig_right, orig_bottom)

        self.accept()
