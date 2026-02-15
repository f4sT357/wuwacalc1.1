import unittest
from unittest.mock import MagicMock
from core.app_logic import AppLogic


class TestAppLogicParsing(unittest.TestCase):
    def setUp(self):
        # Mock dependencies for AppLogic
        self.mock_tr = MagicMock(return_value="translated")
        self.mock_dm = MagicMock()
        self.mock_cm = MagicMock()

        # Instantiate AppLogic
        self.logic = AppLogic(self.mock_tr, self.mock_dm, self.mock_cm)

        # Setup alias pairs (Stat, Alias)
        self.alias_pairs = [
            ("クリティカル率", "クリティカル率"),
            ("クリティカル率", "クリ率"),
            ("クリティカルダメージ", "クリティカルダメージ"),
            ("攻撃力%", "攻撃力%"),
            ("攻撃力", "攻撃力"),
        ]

    def test_parse_single_line_clean(self):
        # Standard clean input
        line = "クリティカル率 6.9%"
        result = self.logic._parse_single_line(line, self.alias_pairs)
        self.assertIsNotNone(result)
        substat, is_percent = result
        self.assertEqual(substat.stat, "クリティカル率")
        self.assertEqual(substat.value, "6.9")
        self.assertTrue(is_percent)

    def test_parse_single_line_alias(self):
        # Alias match
        line = "クリ率 10.5"  # Missing % symbol but should parse number
        result = self.logic._parse_single_line(line, self.alias_pairs)
        self.assertIsNotNone(result)
        substat, is_percent = result
        self.assertEqual(substat.stat, "クリティカル率")
        self.assertEqual(substat.value, "10.5")
        self.assertFalse(is_percent)  # No % found

    def test_parse_single_line_fallback(self):
        # Fallback (no separation)
        line = "攻撃力150"
        result = self.logic._parse_single_line(line, self.alias_pairs)
        self.assertIsNotNone(result)
        substat, is_percent = result
        self.assertEqual(substat.stat, "攻撃力")
        self.assertEqual(substat.value, "150")
        self.assertFalse(is_percent)

    def test_parse_no_match(self):
        line = "Unknown 100"
        result = self.logic._parse_single_line(line, self.alias_pairs)
        self.assertIsNone(result)


class TestAppLogicMainStatDetection(unittest.TestCase):
    def setUp(self):
        self.mock_tr = MagicMock(side_effect=lambda x: x)
        self.mock_dm = MagicMock()
        self.mock_cm = MagicMock()
        self.logic = AppLogic(self.mock_tr, self.mock_dm, self.mock_cm)

        # Setup mock game data
        self.mock_dm.main_stat_options = {
            "4": ["会心率", "会心ダメージ", "攻撃力%"],
            "3": ["属性ダメージ", "攻撃力%"],
            "1": ["攻撃力%", "HP%", "防御力%"],
        }
        self.mock_dm.stat_aliases = {"会心率": ["クリティカル率", "クリ率"], "会心ダメージ": ["クリティカルダメージ"]}

    def test_detect_main_stat_direct_match(self):
        ocr_text = "COST 4\n会心率\n攻撃力"
        result = self.logic.detect_main_stat_from_ocr(ocr_text, "4")
        self.assertEqual(result, "会心率")

    def test_detect_main_stat_alias_match(self):
        ocr_text = "Cost: 4\nクリティカル率\nHP"
        result = self.logic.detect_main_stat_from_ocr(ocr_text, "4")
        self.assertEqual(result, "会心率")

    def test_detect_main_stat_no_cost_provided(self):
        # Even without cost, it should find it if unique or in any list
        ocr_text = "???\n属性ダメージ\nSub: ATK"
        result = self.logic.detect_main_stat_from_ocr(ocr_text, None)
        self.assertEqual(result, "属性ダメージ")

    def test_detect_main_stat_not_found(self):
        ocr_text = "Cost 1\nSome garbage text\nAnother line"
        result = self.logic.detect_main_stat_from_ocr(ocr_text, "1")
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
