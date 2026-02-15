from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, QGroupBox
from utils.constants import OCR_ENGINE_PILLOW


class ImagePreprocessingSettingsDialog(QDialog):
    """Dialog for OCR (Image Preprocessing) settings."""

    def __init__(self, parent):
        super().__init__(parent)
        self.app = parent
        self.setWindowTitle(
            self.app.tr("image_preprocessing_settings")
            if self.app.tr("image_preprocessing_settings") != "image_preprocessing_settings"
            else "Image Preprocessing Settings"
        )
        self.setMinimumSize(300, 100)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        ocr_group = QGroupBox(
            self.app.tr("ocr_settings") if self.app.tr("ocr_settings") != "ocr_settings" else "OCR Settings"
        )
        ocr_layout = QVBoxLayout(ocr_group)

        # Engine selection removed - only Pillow is used now

        layout.addWidget(ocr_group)

        # Behavior Group
        behavior_group = QGroupBox(
            self.app.tr("ocr_behavior") if self.app.tr("ocr_behavior") != "ocr_behavior" else "OCR Behavior"
        )
        behavior_layout = QVBoxLayout(behavior_group)

        from PySide6.QtWidgets import QCheckBox

        self.cb_skip_duplicate = QCheckBox(
            self.app.tr("skip_duplicate_ocr")
            if self.app.tr("skip_duplicate_ocr") != "skip_duplicate_ocr"
            else "Skip input if result matches current data"
        )
        self.cb_skip_duplicate.setChecked(self.app.app_config.skip_duplicate_ocr)
        self.cb_skip_duplicate.setToolTip(
            self.app.tr("tooltip_skip_duplicate_ocr")
            if self.app.tr("tooltip_skip_duplicate_ocr") != "tooltip_skip_duplicate_ocr"
            else "If enabled, OCR results identical to the current tab's data will be ignored.\n"
            "This protects manual edits from being overwritten by accidental re-OCR.\n"
            "This is independent of the History duplicate setting."
        )
        behavior_layout.addWidget(self.cb_skip_duplicate)

        layout.addWidget(behavior_group)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_apply = QPushButton(self.app.tr("apply"))
        btn_apply.clicked.connect(self._apply_settings)

        btn_cancel = QPushButton(self.app.tr("cancel"))
        btn_cancel.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(btn_apply)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

    def _apply_settings(self):
        self.app.app_config.skip_duplicate_ocr = self.cb_skip_duplicate.isChecked()
        self.app.config_manager.save()
        self.accept()
