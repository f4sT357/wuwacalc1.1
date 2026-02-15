import unittest
from core.echo_data import EchoData
from core.data_contracts import EvaluationResult
from utils.constants import (
    STAT_CRIT_RATE, STAT_CRIT_DMG, STAT_ATK_PERCENT, STAT_ER
)

class TestAnalysisFeatures(unittest.TestCase):
    def setUp(self):
        # 共通のベースデータ
        self.config_bundle = {
            "substat_max_values": {
                STAT_CRIT_RATE: 10.5,
                STAT_CRIT_DMG: 21.0,
                STAT_ATK_PERCENT: 11.6,
                STAT_ER: 12.4
            },
            "main_stat_multiplier": 15.0,
            "roll_quality": {},
            "effective_stats": {},
            "cv_weights": {"crit_rate": 2.0, "crit_dmg": 1.0},
            "character_main_stats": {
                "4": "クリティカル率",
                "3": "属性ダメージアップ",
                "1": "攻撃力%"
            },
            "ideal_stats": {
                STAT_CRIT_RATE: 70.0,
                STAT_CRIT_DMG: 240.0,
                STAT_ATK_PERCENT: 80.0,
                STAT_ER: 130.0
            },
            "base_stats": {
                "攻撃力": 1000
            }
        }
        self.weights = {
            STAT_CRIT_RATE: 1.0,
            STAT_CRIT_DMG: 1.0,
            STAT_ATK_PERCENT: 1.0,
            STAT_ER: 0.5
        }

    def test_main_stat_flexibility(self):
        # 理想的
        echo1 = EchoData(3, "気動ダメージアップ", {})
        res1 = echo1.evaluate_comprehensive(self.weights, self.config_bundle)
        self.assertEqual(res1.consistency_advice, "")

        # 許容範囲 (攻撃%)
        echo2 = EchoData(3, "攻撃力%", {})
        res2 = echo2.evaluate_comprehensive(self.weights, self.config_bundle)
        self.assertIn("有力な選択肢", res2.consistency_advice)

    def test_crit_ratio_105_buffer(self):
        # 1. 103% (100%超えだが105%未満) -> 警告なし
        bundle = self.config_bundle.copy()
        bundle["stat_offsets"] = {
            STAT_CRIT_RATE: 103.0,
            STAT_CRIT_DMG: 300.0 # 加算200
        }
        echo = EchoData(3, "焦熱ダメージアップ", {})
        result = echo.evaluate_comprehensive(self.weights, bundle)
        
        self.assertFalse(any("大きく超えています" in a for a in result.advice_list))
        # ただし内部では100%として扱われるので、1:2 (100:200) で不足警告は出ないはず
        self.assertFalse(any("優先的に稼ぐのが効率的" in a for a in result.advice_list))

        # 2. 107% (105%超え) -> 警告あり
        bundle["stat_offsets"][STAT_CRIT_RATE] = 107.0
        result2 = echo.evaluate_comprehensive(self.weights, bundle)
        self.assertTrue(any("大きく超えています" in a for a in result2.advice_list))

    def test_crit_ratio_need_more_rate(self):
        # 会心ダメージが高いのに率が低い場合
        bundle = self.config_bundle.copy()
        bundle["stat_offsets"] = {
            STAT_CRIT_RATE: 40.0,
            STAT_CRIT_DMG: 300.0 # 加算200
        }
        echo = EchoData(3, "攻撃力%", {})
        result = echo.evaluate_comprehensive(self.weights, bundle)
        
        # 40 < (200/2)*0.8 = 80 なので警告が出るはず
        self.assertTrue(any("会心率をもう少し上げると" in a for a in result.advice_list))

    def test_build_advice_er(self):
        bundle = self.config_bundle.copy()
        bundle["stat_offsets"] = {STAT_ER: 100.0}
        echo = EchoData(1, "攻撃力%", {})
        result = echo.evaluate_comprehensive(self.weights, bundle)
        self.assertTrue(any("共鳴効率が足りていません" in a for a in result.advice_list))

if __name__ == '__main__':
    unittest.main()
