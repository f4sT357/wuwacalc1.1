from typing import Any, List, Optional, Dict
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QComboBox,
    QPushButton,
    QGroupBox,
    QScrollArea,
    QWidget,
    QGridLayout,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QImage
from core.data_contracts import OCRResult, SubStat
from PIL import Image, ImageQt

class OCRVerificationDialog(QDialog):
    """
    Dialog for verifying and correcting OCR results.
    Shows the cropped image and allows editing recognized stats.
    """

    def __init__(self, parent, ocr_data: OCRResult, cropped_image: Image.Image):
        super().__init__(parent)
        self.app = parent
        self.ocr_data = ocr_data
        self.cropped_image = cropped_image
        self.result_data: Optional[OCRResult] = None

        self.setWindowTitle(self.app.tr("ocr_verification_title", "OCR結果の確認・修正"))
        self.resize(600, 700)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Instruction
        instruction = QLabel(self.app.tr("ocr_verification_instruction", "認識されたステータスを確認し、必要に応じて修正してください。"))
        instruction.setWordWrap(True)
        layout.addWidget(instruction)

        # Image Preview Area
        img_group = QGroupBox(self.app.tr("ocr_image", "OCR画像"))
        img_layout = QVBoxLayout(img_group)
        
        self.img_label = QLabel()
        self.img_label.setAlignment(Qt.AlignCenter)
        self._set_image_preview(self.cropped_image)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self.img_label)
        scroll_area.setMaximumHeight(300)
        img_layout.addWidget(scroll_area)
        
        layout.addWidget(img_group)

        # Stats Editing Area
        stats_group = QGroupBox(self.app.tr("calc_result", "計算機入力項目"))
        stats_layout = QGridLayout(stats_group)

        # Main Stat
        stats_layout.addWidget(QLabel(self.app.tr("main_stat", "メイン")), 0, 0)
        self.main_stat_combo = QComboBox()
        # Get all possible main stats from data_manager if cost is known
        all_main_options = []
        dm = self.app.data_manager
        if self.ocr_data.cost:
            all_main_options = dm.main_stat_options.get(self.ocr_data.cost, [])
        else:
            for opts in dm.main_stat_options.values():
                all_main_options.extend(opts)
            all_main_options = list(set(all_main_options))
        
        self.main_stat_combo.addItems([""] + all_main_options)
        if self.ocr_data.main_stat:
            self.main_stat_combo.setCurrentText(self.ocr_data.main_stat)
        stats_layout.addWidget(self.main_stat_combo, 0, 1)

        # Substats (up to 5)
        self.substat_widgets = []
        all_sub_options = list(dm.substat_max_values.keys())

        for i in range(5):
            row = i + 1
            stats_layout.addWidget(QLabel(self.app.tr("substats", "サブ") + f" {i+1}"), row, 0)
            
            h_layout = QHBoxLayout()
            combo = QComboBox()
            combo.addItems([""] + all_sub_options)
            
            val_edit = QLineEdit()
            val_edit.setPlaceholderText("0.0")
            val_edit.setFixedWidth(80)

            if i < len(self.ocr_data.substats):
                sub = self.ocr_data.substats[i]
                combo.setCurrentText(sub.stat)
                val_edit.setText(sub.value)

            h_layout.addWidget(combo)
            h_layout.addWidget(val_edit)
            stats_layout.addLayout(h_layout, row, 1)
            
            self.substat_widgets.append((combo, val_edit))

        layout.addWidget(stats_group)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_apply = QPushButton(self.app.tr("apply", "適用"))
        btn_apply.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 8px;")
        btn_apply.clicked.connect(self.accept)
        
        btn_cancel = QPushButton(self.app.tr("cancel", "キャンセル"))
        btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(btn_apply)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

    def _set_image_preview(self, pil_img: Image.Image):
        qim = ImageQt.ImageQt(pil_img)
        pixmap = QPixmap.fromImage(qim)
        # Scale if too wide while maintaining aspect ratio
        if pixmap.width() > 550:
            pixmap = pixmap.scaledToWidth(550, Qt.SmoothTransformation)
        self.img_label.setPixmap(pixmap)

    def get_verified_data(self) -> OCRResult:
        """Construct a new OCRResult from the edited fields."""
        new_substats = []
        for combo, edit in self.substat_widgets:
            stat_name = combo.currentText()
            val_text = edit.text().strip()
            if stat_name and val_text:
                new_substats.append(SubStat(stat=stat_name, value=val_text))
        
        return OCRResult(
            substats=new_substats,
            log_messages=self.ocr_data.log_messages,
            cost=self.ocr_data.cost,
            main_stat=self.main_stat_combo.currentText() or None,
            raw_text=self.ocr_data.raw_text,
            boxes=self.ocr_data.boxes
        )
