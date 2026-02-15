import unittest
from core.data_contracts import EchoEntry, SubStat
from managers.tab_manager import TabManager


class DummyApp:
    def __init__(self):
        self.notebook = None
        self.current_config_key = None
        self.data_manager = type("dm", (), {"tab_configs": {}})()
        self.gui_log = print
        self.ui = type("ui", (), {"character_combo": None})()
        self.character_var = ""
        self.auto_apply_main_stats = False


class TestTabManagerDuplicates(unittest.TestCase):
    def setUp(self):
        self.app = DummyApp()
        # Mock dependencies for TabManager
        self.data_manager = self.app.data_manager
        self.config_manager = type(
            "cm",
            (),
            {"get_app_config": lambda: type("cfg", (), {"character_var": "", "auto_apply_main_stats": False})()},
        )()
        self.tr = lambda x: x
        self.character_manager = type("char_mgr", (), {"get_main_stats": lambda self, name: {}})()

        self.tab_mgr = TabManager(
            self.app.notebook, self.data_manager, self.config_manager, self.tr, self.character_manager
        )
        # テスト用のタブデータを直接セット
        self.tab_mgr.tabs_content = {
            "tab1": {},
            "tab2": {},
            "tab3": {},
        }

    def test_find_duplicate_entries(self):
        # 完全一致2件、1件ユニーク
        entries = [
            EchoEntry(tab_index=0, cost="4", main_stat="HP", substats=[SubStat("攻撃", "10"), SubStat("会心", "5")]),
            EchoEntry(tab_index=1, cost="4", main_stat="HP", substats=[SubStat("攻撃", "10"), SubStat("会心", "5")]),
            EchoEntry(tab_index=2, cost="4", main_stat="ATK", substats=[SubStat("攻撃", "10"), SubStat("会心", "5")]),
        ]
        dup_ids = TabManager.find_duplicate_entries(entries)
        self.assertEqual(dup_ids, [1])

    def test_no_duplicates(self):
        entries = [
            EchoEntry(tab_index=0, cost="4", main_stat="HP", substats=[SubStat("攻撃", "10")]),
            EchoEntry(tab_index=1, cost="4", main_stat="HP", substats=[SubStat("攻撃", "11")]),
        ]
        dup_ids = TabManager.find_duplicate_entries(entries)
        self.assertEqual(dup_ids, [])


if __name__ == "__main__":
    unittest.main()
