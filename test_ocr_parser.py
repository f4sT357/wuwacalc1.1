import unittest
from unittest.mock import MagicMock
from core.ocr_parser import OcrParser
from core.data_contracts import EchoEntry, SubStat

class MockDataManager:
    def __init__(self):
        self.substat_max_values = {
            "攻撃力": 60.0,
            "攻撃力%": 11.6,
            "会心率%": 10.5
        }
        self.main_stat_options = {
            "4": ["会心率", "会心ダメージ", "攻撃力%"],
            "3": ["属性ダメージ", "攻撃力%"],
            "1": ["攻撃力%", "HP%", "防御力%"],
        }
        self.stat_aliases = {
            "会心率": ["クリティカル率", "クリ率"],
            "会心ダメージ": ["クリティカルダメージ"],
            "属性ダメージ": ["属性ダメージUP"]
        }
    
    def get_alias_pairs(self):
        return [
            ("会心率%", "会心率"),
            ("会心率%", "クリ率"),
            ("攻撃力", "攻撃力"),
            ("攻撃力%", "攻撃力%")
        ]

class TestOcrParser(unittest.TestCase):
    def setUp(self):
        self.mock_dm = MockDataManager()
        self.mock_tr = lambda x, *args: x
        self.parser = OcrParser(self.mock_dm, self.mock_tr)

    def test_detect_cost(self):
        text = "COST 4\nEcho Name"
        self.assertEqual(self.parser.detect_cost(text), "4")
        
        text_ja = "コスト: 3\nテスト"
        self.assertEqual(self.parser.detect_cost(text_ja), "3")

    def test_detect_main_stat(self):
        text = "COST 4\nクリティカル率\nサブステ"
        self.assertEqual(self.parser.detect_main_stat(text, "4"), "会心率")

    def test_parse_substats_simple(self):
        text = "攻撃力 50\n会心率 8.5%"
        substats, logs = self.parser.parse_substats(text, "ja")
        
        self.assertEqual(len(substats), 2)
        self.assertEqual(substats[0].stat, "攻撃力")
        self.assertEqual(substats[1].stat, "会心率%")

    def test_clean_numeric_string(self):
        self.assertEqual(self.parser._clean_numeric_string("12,5"), "12.5")
        self.assertEqual(self.parser._clean_numeric_string("I0.o"), "10.0")

    def test_validate_and_correct_substat_ranges(self):
        # Case where OCR read 116 instead of 11.6
        # stat_name "攻撃力%" -> search_name "攻撃力%" -> max_val 11.6
        # val 116.0 > 23.2 -> val = 11.6
        stat, val, is_pct = self.parser.validate_and_correct_substat("攻撃力%", "116", True)
        self.assertEqual(val, "11.6")

    def test_full_parse(self):
        text = "COST 4\n会心率\n攻撃力 40\nクリ率 7.0%"
        result = self.parser.parse(text, "ja")
        
        self.assertEqual(result.cost, "4")
        self.assertEqual(result.main_stat, "会心率")
        self.assertEqual(len(result.substats), 2)

if __name__ == "__main__":
    unittest.main()
