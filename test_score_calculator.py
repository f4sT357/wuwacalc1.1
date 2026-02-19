import unittest
import sys
from unittest.mock import MagicMock, patch, ANY
from core.score_calculator import ScoreCalculator
from core.data_contracts import EchoEntry, SubStat, EvaluationResult
from utils.constants import ACTION_SINGLE

# We need a QApplication for signals to work, but we mock it or ensure it's minimal
from PySide6.QtWidgets import QApplication
if not QApplication.instance():
    app = QApplication(sys.argv)

class TestScoreCalculator(unittest.TestCase):
    def setUp(self):
        self.mock_dm = MagicMock()
        self.mock_cm = MagicMock()
        self.mock_hm = MagicMock()
        self.mock_renderer = MagicMock()
        self.mock_config = MagicMock()

        self.calculator = ScoreCalculator(
            self.mock_dm, self.mock_cm, self.mock_hm, self.mock_renderer, self.mock_config
        )

        # Basic mock setup
        self.mock_dm.substat_max_values = {}
        self.mock_dm.main_stat_multiplier = {}
        self.mock_dm.cv_weights = {}
        
        self.app_config = MagicMock()
        self.app_config.history_duplicate_mode = "latest"
        self.mock_config.get_app_config.return_value = self.app_config
        self.mock_cm.get_stat_weights.return_value = {"ATK": 1.0}
        self.mock_dm.get_main_stats.return_value = {}

    @patch("core.score_calculator.EchoData")
    def test_process_echo_evaluation(self, MockEchoData):
        entry = EchoEntry(0, "4", "ATK%", [SubStat("Crit Rate", "10.0")])
        weights = {"Crit Rate": 1.0}
        config = {"cv_weights": {}, "substat_max_values": {}}
        methods = {"normalized": True}

        mock_echo_instance = MockEchoData.return_value
        mock_echo_instance.get_fingerprint.return_value = "hash123"
        mock_eval_result = EvaluationResult(100.0, 1, "S", "S", {"normalized": 100.0})
        mock_echo_instance.evaluate_comprehensive.return_value = mock_eval_result

        result = self.calculator._process_echo_evaluation(
            entry, weights, config, methods, "Char1", ACTION_SINGLE, "Tab1"
        )

        self.assertEqual(result.total_score, 100.0)
        self.mock_hm.add_entry.assert_called_once()

    def test_calculate_single_flow(self):
        # Verify the flow of calculate_single
        entry = EchoEntry(0, "4", "Main", [])
        methods = {"normalized": True}

        with patch.object(self.calculator, "_process_echo_evaluation") as mock_process:
            mock_process.return_value = EvaluationResult(90.0, 2, "A", "A", {"normalized": 90.0})
            self.mock_cm.get_equipped_echo.return_value = None # No comparison call
            
            self.calculator.calculate_single("Char1", "Tab1", entry, methods)

            mock_process.assert_called_once()
            self.mock_renderer.render_single_score.assert_called_once()

    def test_format_eval_data_for_batch(self):
        eval_result = EvaluationResult(85.5, 3, "B", "B", {"normalized": 85.5})
        
        # Mock translations
        with patch("utils.languages.TRANSLATIONS", {"en": {"B": "B_Rank"}}):
            result = self.calculator._format_eval_data_for_batch("Tab_X", eval_result, "en")
            self.assertEqual(result["tab_name"], "Tab_X")
            self.assertEqual(result["total"], 85.5)
            self.assertEqual(result["recommendation"], "B_Rank")

if __name__ == "__main__":
    unittest.main()


if __name__ == "__main__":
    unittest.main()
