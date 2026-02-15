import unittest
from unittest.mock import MagicMock, patch
from core.data_contracts import EchoEntry, SubStat
from managers.tab_manager import TabManager
from managers.character_manager import CharacterManager

class TestCharacterPresetAssignment(unittest.TestCase):
    def setUp(self):
        # Mock dependencies
        self.mock_notebook = MagicMock()
        self.mock_data_manager = MagicMock()
        self.mock_config_manager = MagicMock()
        self.mock_tr = lambda x, *args: x
        self.mock_logger = MagicMock()
        
        # Setup AppConfig mock
        self.mock_app_config = MagicMock()
        self.mock_app_config.current_config_key = "43311"
        self.mock_app_config.auto_apply_main_stats = True
        self.mock_config_manager.get_app_config.return_value = self.mock_app_config
        
        # Setup TabConfigs
        self.mock_data_manager.tab_configs = {
            "43311": ["4", "3_1", "3_2", "1_1", "1_2"]
        }
        self.mock_data_manager.main_stat_options = {
            "4": ["会心率", "会心ダメージ"],
            "3": ["属性ダメージ"],
            "1": ["攻撃力%"]
        }
        self.mock_data_manager.substat_max_values = {
            "会心率": 10.5,
            "攻撃力": 100
        }

        # Setup CharacterManager
        self.char_mgr = CharacterManager(self.mock_logger, self.mock_data_manager)
        self.char_mgr.get_main_stats = MagicMock(return_value={
            "4": "会心率",
            "3_1": "属性ダメージ",
            "3_2": "属性ダメージ",
            "1_1": "攻撃力%",
            "1_2": "攻撃力%"
        })
        
        # Mock equipped echoes
        self.test_char = "TestChar"
        self.preset_echo_4 = EchoEntry(
            tab_index=0, cost="4", main_stat="会心率",
            substats=[SubStat("攻撃力", "100"), SubStat("会心率", "10.5")]
        )
        self.char_mgr._equipped_echoes = {
            self.test_char: {
                "4": self.preset_echo_4
            }
        }
        
        # Instantiate TabManager
        self.tab_mgr = TabManager(self.mock_notebook, self.mock_data_manager, self.mock_config_manager, self.mock_tr, self.char_mgr)
        
        # Manually setup tabs_content to avoid full UI initialization
        self.tabs_content = {}
        for tab_name in self.mock_data_manager.tab_configs["43311"]:
            cost_num = tab_name[0]
            main_widget = MagicMock()
            main_widget.findData.return_value = 0 # Default to first item
            sub_entries = []
            for _ in range(5):
                stat_widget = MagicMock()
                stat_widget.findData.return_value = 0
                val_widget = MagicMock()
                sub_entries.append((stat_widget, val_widget))
            
            self.tabs_content[tab_name] = {
                "cost": cost_num,
                "main_widget": main_widget,
                "sub_entries": sub_entries
            }
        self.tab_mgr.tabs_content = self.tabs_content

    def test_apply_main_stats_only(self):
        """
        Tests if the existing main stat recommendation is correctly applied.
        """
        # Triggers the logic
        self.tab_mgr.apply_character_main_stats(character=self.test_char)
        
        # Check Tab "4"
        tab_4 = self.tabs_content["4"]
        main_combo = tab_4["main_widget"]
        
        # Verify findData was called with "会心率" (the recommendation)
        found_target = False
        for call in main_combo.findData.call_args_list:
            if call[0][0] == "会心率":
                found_target = True
                break
        self.assertTrue(found_target, "Main stat recommendation was not used")

    def test_apply_equipped_echoes_including_substats(self):
        """
        Tests if full echo data (including substats) from presets is assigned.
        Note: This is expected to FAIL with the current implementation.
        """
        # Mock findData for substat combos
        def mock_find_data(data):
            return 1 if data != "" else -1
        
        for tab_name, content in self.tabs_content.items():
            for stat_combo, _ in content["sub_entries"]:
                stat_combo.findData.side_effect = mock_find_data

        # Triggers the logic
        self.tab_mgr.apply_character_main_stats(character=self.test_char)
        
        # Check Tab "4"
        tab_4 = self.tabs_content["4"]
        sub_entries = tab_4["sub_entries"]
        
        # Look for "攻撃力" preset value "100"
        found_val = False
        for _, val_edit in sub_entries:
             if val_edit.setText.called:
                 args, _ = val_edit.setText.call_args
                 if args[0] == "100":
                     found_val = True
                     break
        
        self.assertTrue(found_val, "Full echo preset (substats) was not assigned")

if __name__ == '__main__':
    unittest.main()
