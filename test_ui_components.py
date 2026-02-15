import sys
import unittest
from unittest.mock import MagicMock
from PySide6.QtWidgets import QApplication, QMainWindow

# Ensure QApplication exists only once
app_instance = QApplication.instance()
if not app_instance:
    app_instance = QApplication(sys.argv)

from ui.ui_components import UIComponents


class TestUIComponents(unittest.TestCase):
    def setUp(self):
        # Use QMainWindow to satisfy QObject type checks
        self.mock_app = QMainWindow()

        # Mock tr method
        self.mock_app.tr = MagicMock(side_effect=lambda x: f"tr_{x}")

        # Mock data manager
        self.mock_app.data_manager = MagicMock()
        self.mock_app.data_manager.tab_configs = {"default": []}

        # Mock app properties
        self.mock_app.current_config_key = "default"
        self.mock_app.language = "en"
        self.mock_app.mode_var = "manual"
        self.mock_app.score_mode_var = "batch"
        self.mock_app.auto_apply_main_stats = True

        # Mock app_config
        self.mock_app.app_config = MagicMock()
        self.mock_app.app_config.enabled_calc_methods = {}
        self.mock_app.app_config.crop_left_percent = 0.0
        self.mock_app.app_config.crop_top_percent = 0.0
        self.mock_app.app_config.crop_width_percent = 0.0
        self.mock_app.app_config.crop_height_percent = 0.0
        self.mock_app.crop_mode_var = "percent"

        # Mock events handler
        self.mock_app.events = MagicMock()

        # Mock other dependencies accessed in create_main_layout
        self.mock_app.score_calc = MagicMock()
        self.mock_app.tab_mgr = MagicMock()
        self.mock_app.image_proc = MagicMock()
        self.mock_app._open_readme = MagicMock()
        self.mock_app.open_display_settings = MagicMock()
        self.mock_app.open_image_preprocessing_settings = MagicMock()
        self.mock_app.open_history = MagicMock()
        self.mock_app.open_char_settings_new = MagicMock()
        self.mock_app.open_char_settings_edit = MagicMock()

        # Mock image related attributes
        self.mock_app.loaded_image = None
        self.mock_app.image_label = None

        # Notebook needed for UIComponents init
        self.mock_app.notebook = MagicMock()

        self.ui = UIComponents(self.mock_app)

    def test_layout_creation(self):
        """Test that create_main_layout correctly constructs the UI hierarchy."""
        try:
            self.ui.create_main_layout()
        except Exception as e:
            self.fail(f"create_main_layout raised exception: {e}")

        self.assertIsNotNone(self.ui.main_widget)
        self.assertIsNotNone(self.ui.settings_group)


if __name__ == "__main__":
    unittest.main()
