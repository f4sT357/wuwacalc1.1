import unittest
from core.echo_data import EchoData
from utils.constants import STAT_ATK_PERCENT, STAT_ATK_FLAT, STAT_CRIT_RATE


class TestStatCalculation(unittest.TestCase):
    def setUp(self):
        # Sample setup for an Echo
        self.substats = {STAT_ATK_PERCENT: 10.0, STAT_ATK_FLAT: 50.0, STAT_CRIT_RATE: 8.0}
        self.echo = EchoData(cost=4, main_stat=STAT_ATK_PERCENT, substats=self.substats)

        # Calculation config bundle
        self.config_bundle = {
            "substat_max_values": {STAT_ATK_PERCENT: 11.6, STAT_ATK_FLAT: 60.0, STAT_CRIT_RATE: 10.5},
            "main_stat_multiplier": 15.0,
            "roll_quality": {},
            "effective_stats": {},
            "cv_weights": {},
        }

        # Character weights
        self.weights = {STAT_ATK_PERCENT: 1.0, STAT_ATK_FLAT: 0.5, STAT_CRIT_RATE: 1.0}

    def test_total_stat_calculation(self):
        """Test if final stat (Total ATK) is calculated correctly with base and offsets."""
        base_stats = {"攻撃力": 1000.0}
        stat_offsets = {
            STAT_ATK_PERCENT: 20.0,  # Weapon/Other Echoes
            STAT_ATK_FLAT: 100.0,  # Other Echoes flat
            STAT_CRIT_RATE: 5.0,
        }
        ideal_stats = {"攻撃力": 2000.0}

        # Calculation:
        # Base ATK = 1000
        # Total ATK% = 10 (Echo) + 20 (Offset) = 30%
        # Total ATK Flat = 50 (Echo) + 100 (Offset) = 150
        # Expected Final ATK = (1000 * (1 + 30/100)) + 150 = 1300 + 150 = 1450
        # Achievement towards ideal = 1450 / 2000 = 72.5%

        evaluation = self.echo.evaluate_comprehensive(
            self.weights,
            self.config_bundle,
            stat_offsets=stat_offsets,
            base_stats=base_stats,
            ideal_stats=ideal_stats,
            scaling_stat="攻撃力",
        )

        self.assertIn("Total 攻撃力", evaluation.estimated_stats)
        self.assertEqual(evaluation.estimated_stats["Total 攻撃力"], 1450.0)
        self.assertIn("Goal 攻撃力 %", evaluation.estimated_stats)
        self.assertEqual(evaluation.estimated_stats["Goal 攻撃力 %"], 72.5)

    def test_scaling_stat_switch(self):
        """Test switching scaling stat to HP."""
        from utils.constants import STAT_HP_FLAT, STAT_HP_PERCENT

        base_stats = {STAT_HP_FLAT: 10000.0}
        stat_offsets = {STAT_HP_PERCENT: 50.0, STAT_HP_FLAT: 2000.0}
        ideal_stats = {STAT_HP_FLAT: 20000.0}

        # Add HP stats to echo
        self.echo.substats[STAT_HP_PERCENT] = 10.0
        self.echo.substats[STAT_HP_FLAT] = 500.0

        # Calculation:
        # Base HP = 10000
        # Total HP% = 10 + 50 = 60%
        # Total HP Flat = 500 + 2000 = 2500
        # Final HP = (10000 * 1.6) + 2500 = 16000 + 2500 = 18500

        evaluation = self.echo.evaluate_comprehensive(
            self.weights,
            self.config_bundle,
            stat_offsets=stat_offsets,
            base_stats=base_stats,
            ideal_stats=ideal_stats,
            scaling_stat=STAT_HP_FLAT,
        )

        self.assertEqual(evaluation.estimated_stats[f"Total {STAT_HP_FLAT}"], 18500.0)


if __name__ == "__main__":
    unittest.main()
