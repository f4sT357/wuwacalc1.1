import unittest
import sys
from unittest.mock import MagicMock, patch, ANY
from core.score_calculator import ScoreCalculator
from core.data_contracts import EchoEntry, SubStat, EvaluationResult
from utils.constants import ACTION_SINGLE
from PySide6.QtWidgets import QApplication

# Initialize QApplication for signals
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

        # Setup mocks for dependencies
        self.mock_dm.substat_max_values = {}
        self.mock_dm.main_stat_multiplier = {}
        self.mock_dm.roll_quality_config = {}
        self.mock_dm.effective_stats_config = {}
        self.mock_dm.cv_weights = {}

        self.app_config = MagicMock()
        self.app_config.history_duplicate_mode = "latest"
        self.mock_config.get_app_config.return_value = self.app_config

    @patch("core.score_calculator.EchoData")
    def test_process_echo_evaluation(self, MockEchoData):
        # Setup input
        entry = EchoEntry(0, "4", "ATK%", [SubStat("Crit Rate", "10.0")])
        weights = {"Crit Rate": 1.0}
        config = {}
        methods = {"normalized": True}

        # Mock EchoData behavior
        mock_echo_instance = MockEchoData.return_value
        mock_echo_instance.get_fingerprint.return_value = "hash123"
        mock_eval_result = EvaluationResult(100.0, 1, "S", "S", {})
        mock_echo_instance.evaluate_comprehensive.return_value = mock_eval_result

        # Run
        result = self.calculator._process_echo_evaluation(
            entry, weights, config, methods, "Char1", ACTION_SINGLE, "Tab1"
        )

        # Verify
        self.assertIsNotNone(result)
        self.assertEqual(result.total_score, 100.0)

        # Verify History Add
        self.mock_hm.add_entry.assert_called_once_with(
            character="Char1",
            cost="4",
            action=ACTION_SINGLE,
            result=ANY,
            fingerprint="hash123",
            details={"score": 100.0, "rating_key": "S"},
            duplicate_mode="latest",
        )

    def test_calculate_single_calls_process(self):
        # Test that calculate_single correctly calls _process_echo_evaluation
        entry = EchoEntry(0, "4", "Main", [])
        methods = {"method": True}

        with patch.object(self.calculator, "_process_echo_evaluation") as mock_process:
            mock_process.return_value = EvaluationResult(100.0, 1, "S", "S", {})

            # Connect signal to verify
            self.calculator.single_calculation_completed.connect(lambda html, tab, eval: None)

            self.calculator.calculate_single("Char1", "Tab1", entry, methods)

            mock_process.assert_called_once()
            self.mock_renderer.render_single_score.assert_called_once()

    def test_format_eval_data_for_batch(self):
        # Test formatting logic
        eval_result = EvaluationResult(100.0, 1, "S", "S", {"normalized": 100.0})

        with patch("utils.languages.TRANSLATIONS", {"en": {"S": "S_Rank"}}):
            result = self.calculator._format_eval_data_for_batch("Tab1", eval_result, "en")

            self.assertEqual(result["tab_name"], "Tab1")
            self.assertEqual(result["total"], 100.0)
            self.assertEqual(result["recommendation"], "S_Rank")
            self.assertEqual(result["normalized"], 100.0)


if __name__ == "__main__":
    unittest.main()
