import unittest
from core.echo_data import EchoData
from core.data_contracts import SubStat, EchoEntry


class TestEchoData(unittest.TestCase):
    def setUp(self):
        self.cost = "4"
        self.main_stat = "Crit. Rate"
        self.substats = {
            "Crit. DMG": 12.6,
            "ATK": 6.4,
            "Energy Regen": 10.0,
            "Resonance Skill DMG Bonus": 8.6,
            "Basic Attack DMG Bonus": 8.1,
        }
        self.echo = EchoData(self.cost, self.main_stat, self.substats)

    def test_init(self):
        self.assertEqual(self.echo.cost, "4")
        self.assertEqual(self.echo.main_stat, "Crit. Rate")
        self.assertEqual(len(self.echo.substats), 5)

    def test_evaluate_normalized(self):
        # Mock dependencies
        weights = {
            "Crit. DMG": 1.0,
            "ATK": 0.5,
            "Energy Regen": 0.8,
            "Resonance Skill DMG Bonus": 0.6,
            "Basic Attack DMG Bonus": 0.0,
        }
        # Assuming DataManager provides these, we'll mock the lookup or config bundle
        substat_max_values = {
            "Crit. DMG": 21.0,
            "ATK": 11.6,  # %
            "Energy Regen": 14.9,  # % (approx)
            "Resonance Skill DMG Bonus": 10.9,  # %
            "Basic Attack DMG Bonus": 11.6,
        }
        main_stat_multiplier = 0.0

        # Test Normalized calculation
        score = self.echo.calculate_score_normalized(weights, substat_max_values, main_stat_multiplier)
        self.assertIsInstance(score, float)
        self.assertGreater(score, 0.0)
        self.assertLessEqual(score, 100.0)

    def test_evaluate_crit_value(self):
        # CV = CR * 2 + CD
        # Implementation hardcodes Japanese keys for CV calculation currently
        jp_substats = {"クリティカルダメージ": 12.6, "クリティカル率": 0.0}
        echo_jp = EchoData(self.cost, self.main_stat, jp_substats)

        weights = {
            "crit_rate": 2.0,
            "crit_dmg": 1.0,
            "atk_percent": 0.0,
            "atk_flat_divisor": 1.0,
            "atk_flat_multiplier": 0.0,
            "er": 0.0,
        }
        stat_weights = {"クリティカル率": 1.0, "クリティカルダメージ": 1.0}

        # Substats: Crit. DMG 12.6
        # Expected: 12.6 * 1.0 = 12.6
        score = echo_jp.calculate_score_cv_based(stat_weights, weights)
        self.assertAlmostEqual(score, 12.6)

    def test_evaluate_comprehensive(self):
        # Mock dependencies
        weights = {"Crit. DMG": 1.0, "ATK": 0.5}
        config_bundle = {
            "substat_max_values": {"Crit. DMG": 21.0, "ATK": 11.6},
            "main_stat_multiplier": 15.0,
            "roll_quality": {},
            "effective_stats": {},
            "cv_weights": {"crit_rate": 2.0, "crit_dmg": 1.0},
        }

        result = self.echo.evaluate_comprehensive(weights, config_bundle)
        self.assertIn("total_score", result)
        self.assertIn("individual_scores", result)

    def test_entry_contracts(self):
        sub_list = [SubStat(stat="ATK", value="10%")]
        entry = EchoEntry(tab_index=0, cost="3", main_stat="Havoc DMG Bonus", substats=sub_list)
        self.assertEqual(entry.cost, "3")
        self.assertEqual(entry.substats[0].value, "10%")


if __name__ == "__main__":
    unittest.main()
