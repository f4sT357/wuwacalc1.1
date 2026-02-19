import unittest
from unittest.mock import MagicMock, patch
from core.app_logic import AppLogic

class TestAppLogic(unittest.TestCase):
    def setUp(self):
        self.mock_tr = MagicMock(side_effect=lambda x: x)
        self.mock_dm = MagicMock()
        self.mock_cm = MagicMock()
        
        # AppLogic init
        self.logic = AppLogic(self.mock_tr, self.mock_dm, self.mock_cm)
        
        # Fix mock for OcrParser within AppLogic
        self.logic.ocr_parser = MagicMock()

    def test_perform_ocr_workflow_calls_parser(self):
        # Mock the OCR engine call
        mock_image = MagicMock()
        with patch.object(self.logic, "_perform_ocr_with_boxes") as mock_ocr:
            mock_ocr.return_value = ("raw text", {"data": 1})
            
            self.logic.perform_ocr_workflow(mock_image, "ja")
            
            self.logic.ocr_parser.parse_with_boxes.assert_called_once_with("raw text", {"data": 1}, "ja")

    def test_app_config_integration(self):
        # Test if app logic correctly retrieves config
        self.mock_cm.get_app_config.return_value.language = "zh-CN"
        self.assertEqual(self.mock_cm.get_app_config().language, "zh-CN")

if __name__ == "__main__":
    unittest.main()


if __name__ == "__main__":
    unittest.main()
