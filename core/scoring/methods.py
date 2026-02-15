from typing import Dict, Any, Optional
from core.scoring.base import ScoringStrategy
from utils.constants import (
    STAT_CRIT_RATE,
    STAT_CRIT_DMG,
    STAT_ATK_PERCENT,
    STAT_ATK_FLAT,
    STAT_ER,
    CV_KEY_CRIT_RATE,
    CV_KEY_CRIT_DMG,
    CV_KEY_ATK_PERCENT,
    CV_KEY_ATK_FLAT_DIVISOR,
    CV_KEY_ATK_FLAT_MULTIPLIER,
    CV_KEY_ER,
    CV_KEY_DMG_BONUS,
    DAMAGE_BONUS_STATS,
)

class NormalizedScoring(ScoringStrategy):
    def name(self) -> str:
        return "normalized"

    def calculate(self, echo: Any, stat_weights: Dict[str, float], config: Dict[str, Any]) -> float:
        max_vals = config.get("substat_max_values", {})
        main_mult = config.get("main_stat_multiplier", 15.0)
        
        main_score = main_mult
        sub_score = 0.0
        for stat_name, stat_value in echo.substats.items():
            max_val = max_vals.get(stat_name, 1.0)
            weight = stat_weights.get(stat_name, 0.0)
            normalized = (stat_value / max_val / 5.0) * weight * 100.0
            sub_score += normalized

        return (echo.level / 25.0) * (main_score + sub_score)

class RatioScoring(ScoringStrategy):
    def name(self) -> str:
        return "ratio"

    def calculate(self, echo: Any, stat_weights: Dict[str, float], config: Dict[str, Any]) -> float:
        max_vals = config.get("substat_max_values", {})
        score_ratio = 0.0
        for stat_name, stat_value in echo.substats.items():
            max_val = max_vals.get(stat_name, 1.0)
            importance = stat_weights.get(stat_name, 0.0)
            ratio = (stat_value / max_val / 5.0) * importance
            score_ratio += ratio

        return (100.0 * echo.level / 25.0) * score_ratio

class RollQualityScoring(ScoringStrategy):
    def name(self) -> str:
        return "roll"

    def calculate(self, echo: Any, stat_weights: Dict[str, float], config: Dict[str, Any]) -> float:
        rq_config = config.get("roll_quality", {})
        if not rq_config:
            return 0.0

        ranges_cfg = rq_config.get("ranges", {})
        points_cfg = rq_config.get("points", {})
        quality_points = 0.0
        count = 0

        for stat_name, stat_value in echo.substats.items():
            if stat_name not in ranges_cfg:
                continue

            ranges = ranges_cfg[stat_name]
            weight = stat_weights.get(stat_name, 0.5)

            if stat_value >= ranges.get("Max", 999.0):
                quality_points += points_cfg.get("Max", 3.0) * weight
            elif stat_value >= ranges.get("Good", 999.0):
                quality_points += points_cfg.get("Good", 2.0) * weight
            elif stat_value >= ranges.get("Low", 999.0):
                quality_points += points_cfg.get("Low", 1.0) * weight
            else:
                quality_points += points_cfg.get("Default", 0.5) * weight
            count += 1

        score = (quality_points / (count * 3.0)) * 100.0 if count > 0 else 0.0
        return score * (echo.level / 25.0)

class EffectiveStatsScoring(ScoringStrategy):
    def name(self) -> str:
        return "effective"

    def calculate(self, echo: Any, stat_weights: Dict[str, float], config: Dict[str, Any]) -> float:
        es_config = config.get("effective_stats", {})
        threshold = es_config.get("threshold", 0.5)
        base_mult = es_config.get("base_multiplier", 20.0)
        bonus_mults = es_config.get("bonus_multiplier", {})
        max_vals = config.get("substat_max_values", {})
        
        effective_count = 0
        total_contribution = 0.0
        eps = 1e-9

        for stat_name, stat_value in echo.substats.items():
            weight = stat_weights.get(stat_name, 0.0)
            if weight >= (threshold - eps):
                effective_count += 1
                max_val = max_vals.get(stat_name, 1.0)
                total_contribution += (stat_value / max_val) * weight * base_mult

        bonus = bonus_mults.get(str(effective_count), bonus_mults.get("default", 0.5))
        score = total_contribution * bonus * (echo.level / 25.0)
        # Side effect: updating echo.effective_stats_count is expected by evaluate_comprehensive
        echo.effective_stats_count = effective_count
        return score

class CVScoring(ScoringStrategy):
    def name(self) -> str:
        return "cv"

    def calculate(self, echo: Any, stat_weights: Dict[str, float], config: Dict[str, Any]) -> float:
        cv_weights = config.get("cv_weights", {})
        cv_score = 0.0

        crit_rate = echo.substats.get(STAT_CRIT_RATE, 0.0)
        crit_dmg = echo.substats.get(STAT_CRIT_DMG, 0.0)
        cv_score += (crit_rate * cv_weights.get(CV_KEY_CRIT_RATE, 2.0))
        cv_score += (crit_dmg * cv_weights.get(CV_KEY_CRIT_DMG, 1.0))

        atk_pct = echo.substats.get(STAT_ATK_PERCENT, 0.0)
        flat_atk = echo.substats.get(STAT_ATK_FLAT, 0.0)
        er = echo.substats.get(STAT_ER, 0.0)

        cv_score += atk_pct * cv_weights.get(CV_KEY_ATK_PERCENT, 1.1)
        flat_atk_div = cv_weights.get(CV_KEY_ATK_FLAT_DIVISOR, 10.0)
        flat_atk_mult = cv_weights.get(CV_KEY_ATK_FLAT_MULTIPLIER, 1.2)
        cv_score += (flat_atk / flat_atk_div * flat_atk_mult)
        cv_score += er * cv_weights.get(CV_KEY_ER, 0.5)

        dmg_bonus_weight = cv_weights.get(CV_KEY_DMG_BONUS, 1.1)
        for stat_name in DAMAGE_BONUS_STATS:
            if stat_name in echo.substats:
                val = echo.substats[stat_name]
                weight = stat_weights.get(stat_name, 0.5)
                cv_score += val * dmg_bonus_weight * weight

        return cv_score * (echo.level / 25.0)
