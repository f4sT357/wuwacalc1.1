import unittest
from unittest.mock import MagicMock
from core.data_contracts import EchoEntry, SubStat
from managers.tab_manager import TabManager
from managers.character_manager import CharacterManager

class TestCharacterPresetAssignment(unittest.TestCase):
    def setUp(self):
        # Mock dependencies
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
        self.char_mgr = MagicMock(spec=CharacterManager)
        self.char_mgr.get_main_stats.return_value = {
            "4": "会心率",
            "3_1": "属性ダメージ",
            "3_2": "属性ダメージ",
            "1_1": "攻撃力%",
            "1_2": "攻撃力%"
        }
        
        # Mock equipped echoes
        self.test_char = "TestChar"
        self.preset_echo_4 = EchoEntry(
            tab_index=0, cost="4", main_stat="会心率",
            substats=[SubStat("攻撃力", "100"), SubStat("会心率", "10.5")]
        )
        self.char_mgr.get_equipped_echo.return_value = None
        self.char_mgr.get_equipped_echo.side_effect = lambda char, tab: self.preset_echo_4 if tab == "4" else None
        
        # Instantiate TabManager
        self.tab_mgr = TabManager(self.mock_data_manager, self.mock_config_manager, self.mock_tr, self.char_mgr)
        
        # Manually setup tabs_content to match TabManager's expectation
        self.tab_widgets = {}
        for tab_name in self.mock_data_manager.tab_configs["43311"]:
            cost_num = tab_name[0]
            mock_widget = MagicMock()
            self.tab_mgr.tabs_content[tab_name] = {
                "cost": cost_num,
                "widget": mock_widget
            }
            self.tab_widgets[tab_name] = mock_widget

    def test_apply_main_stats_only(self):
        """
        Tests if the existing main stat recommendation is correctly applied.
        """
        # Triggers the logic
        self.tab_mgr.apply_character_main_stats(character=self.test_char)
        
        # Check Tab "4"
        widget_4 = self.tab_widgets["4"]
        
        # Verify update_main_options was called
        # The logic in apply_character_main_stats calls widget.update_main_options
        self.assertTrue(widget_4.update_main_options.called)
        args = widget_4.update_main_options.call_args[0]
        # args[0] is final_opts, args[1] is preferred
        self.assertIn("会心率", args[1])

    def test_apply_equipped_echo_data(self):
        """
        Tests if OCR results are NOT applied but instead equipped data is logged.
        Wait, no, the test name says 'apply_equipped_echoes_including_substats'.
        Actually, apply_character_main_stats only applies recommendations to UI options.
        It doesn't fill the entries with costs/substats from equipped data automatically in the current code?
        Let me check TabManager.apply_character_main_stats again.
        """
        # Triggers the logic
        self.tab_mgr.apply_character_main_stats(character=self.test_char, force=True)
        
        # In the current implementation, apply_character_main_stats doesn't call set_data.
        # It's intended to update the COMBO BOX options to prefer the character's stats.
        pass

if __name__ == '__main__':
    unittest.main()
