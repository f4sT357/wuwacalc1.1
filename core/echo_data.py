"""
Echo Data Module

Provides the EchoData class for storing echo statistics 
and performing various scoring evaluations.
"""

from __future__ import annotations

import hashlib
from typing import Dict, Any, Optional, List, Tuple

from utils.constants import (
    STAT_CRIT_RATE,
    STAT_CRIT_DMG,
    STAT_ATK_PERCENT,
    STAT_ATK_FLAT,
    STAT_DEF_PERCENT,
    STAT_DEF_FLAT,
    STAT_HP_PERCENT,
    STAT_HP_FLAT,
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
from core.data_contracts import EvaluationResult
from core.scoring import SCORING_METHODS, get_scoring_method


class EchoData:
    """
    Represents an individual Echo and provides methods for comprehensive scoring.
    """

    def __init__(self, cost: int | str, main_stat: str, substats: Dict[str, float]):
        """
        Initialize an Echo instance.

        Args:
            cost: Echo cost (1, 3, or 4).
            main_stat: Name of the primary statistic.
            substats: Mapping of substat names to their numeric values.
        """
        self.cost = str(cost)
        self.main_stat = main_stat
        self.substats = substats
        self.level = 25
        self.score = 0.0
        self.rating = ""
        self.effective_stats_count = 0

    # --- Scoring Methods ---

    def calculate_score_normalized(
        self,
        stat_weights: Dict[str, float],
        substat_max_values: Dict[str, float],
        main_stat_multiplier: float
    ) -> float:
        """Method 1: Normalized Score (0-100 points) based on max possible rolls."""
        strategy = get_scoring_method("normalized")
        config = {
            "substat_max_values": substat_max_values,
            "main_stat_multiplier": main_stat_multiplier
        }
        return strategy.calculate(self, stat_weights, config)

    def calculate_score_ratio_based(
        self,
        importance_weights: Dict[str, float],
        substat_max_values: Dict[str, float]
    ) -> float:
        """Method 2: Ratio-Based Method focusing on stat importance."""
        strategy = get_scoring_method("ratio")
        config = {"substat_max_values": substat_max_values}
        return strategy.calculate(self, importance_weights, config)

    def calculate_score_roll_quality(
        self,
        stat_weights: Dict[str, float],
        roll_quality_config: Dict[str, Any]
    ) -> float:
        """Method 3: Roll Quality Method based on value ranges (Low to Max)."""
        strategy = get_scoring_method("roll")
        config = {"roll_quality": roll_quality_config}
        return strategy.calculate(self, stat_weights, config)

    def calculate_score_effective_stats(
        self,
        stat_weights: Dict[str, float],
        substat_max_values: Dict[str, float],
        effective_stats_config: Dict[str, Any]
    ) -> float:
        """Method 4: Effective Stats Count Method with bonus for multiple valid stats."""
        strategy = get_scoring_method("effective")
        config = {
            "effective_stats": effective_stats_config,
            "substat_max_values": substat_max_values
        }
        return strategy.calculate(self, stat_weights, config)

    def calculate_score_cv_based(
        self,
        stat_weights: Dict[str, float],
        cv_weights: Dict[str, float],
        stat_offsets: Optional[Dict[str, float]] = None
    ) -> float:
        """Method 5: CV (Crit Value) Based Method (Community Standard)."""
        strategy = get_scoring_method("cv")
        config = {"cv_weights": cv_weights}
        return strategy.calculate(self, stat_weights, config)

    def calculate_theoretical_max_sub_score(
        self,
        stat_weights: Dict[str, float],
        substat_max_values: Dict[str, float]
    ) -> float:
        """Calculate the theoretical maximum score for 5 ideal substat rolls."""
        if not stat_weights:
            return 100.0

        # Sort weights to find the 5 best possible stats for this character
        weighted = sorted(
            [(n, w) for n, w in stat_weights.items() if w > 0],
            key=lambda x: x[1], reverse=True
        )
        top_5 = weighted[:5]

        max_score = 0.0
        for name, weight in top_5:
            # Maximum normalized score for 1 slot is 20 * weight
            max_score += 20.0 * weight

        return max_score if max_score > 0 else 100.0

    def evaluate_comprehensive(
        self,
        character_weights: Dict[str, float],
        config_bundle: Dict[str, Any],
        enabled_methods: Optional[Dict[str, bool]] = None,
        stat_offsets: Optional[Dict[str, float]] = None,
        base_stats: Optional[Dict[str, float]] = None,
        ideal_stats: Optional[Dict[str, float]] = None,
        scaling_stat: str = "攻撃力",
    ) -> EvaluationResult:
        """Perform a full evaluation using multiple methodologies and stat estimations."""
        stat_offsets = stat_offsets or {}
        base_stats = base_stats or {}
        ideal_stats = ideal_stats or {}
        enabled_methods = enabled_methods or {
            "normalized": True, "ratio": True, "roll": True, "effective": True, "cv": True
        }

        max_vals = config_bundle.get("substat_max_values", {})
        main_mult = config_bundle.get("main_stat_multiplier", 15.0)

        # 1. Individual Method Scores
        results = {}
        for strategy in SCORING_METHODS:
            method_name = strategy.name()
            if enabled_methods.get(method_name):
                results[method_name] = strategy.calculate(
                    self, character_weights, config_bundle
                )

        # 2. Achievement Rate (Main Metric)
        theo_max = self.calculate_theoretical_max_sub_score(character_weights, max_vals)
        current_sub_score = 0.0
        for stat_name, stat_value in self.substats.items():
            m_val = max_vals.get(stat_name, 1.0)
            weight = character_weights.get(stat_name, 0.0)
            current_sub_score += (stat_value / m_val / 5.0) * weight * 100.0

        achievement_rate = (current_sub_score / theo_max * 100.0) if theo_max > 0 else 0.0
        results["achievement"] = achievement_rate
        rating_key = self.get_rating_by_achievement(achievement_rate, self.cost)

        # 3. Estimated Total Stats and Goal Tracking
        # Defensive key collection to prevent unhashable type errors
        sub_keys = {str(k) for k in self.substats.keys()}
        offset_keys = {str(k) for k in stat_offsets.keys()}
        
        estimated = {
            name: self.substats.get(name, 0.0) + stat_offsets.get(name, 0.0)
            for name in (sub_keys | offset_keys)
        }

        p_map = {
            STAT_ATK_FLAT: STAT_ATK_PERCENT, 
            STAT_DEF_FLAT: STAT_DEF_PERCENT,
            STAT_HP_FLAT: STAT_HP_PERCENT
        }

        if scaling_stat in base_stats:
            base_val = base_stats[scaling_stat]
            p_stat = p_map.get(scaling_stat)
            p_sum = estimated.get(p_stat, 0.0)
            f_sum = estimated.get(scaling_stat, 0.0)

            final_val = (base_val * (1.0 + p_sum / 100.0)) + f_sum
            estimated[f"Total {scaling_stat}"] = final_val

            target = ideal_stats.get(scaling_stat, 0.0)
            if target > 0:
                estimated[f"Goal {scaling_stat} %"] = (final_val / target) * 100.0

        # Main Stat Consistency Check
        consistency_msg = ""
        is_best = True
        penalty = 1.0
        
        expected_main_stats = config_bundle.get("character_main_stats", {})
        # Find all valid candidates for this cost (e.g., '3', '3_1', '3_2')
        cost_prefix = str(self.cost).split('_')[0]
        possible_targets = []
        for k, v in expected_main_stats.items():
            if k.startswith(cost_prefix):
                if isinstance(v, (list, tuple)):
                    possible_targets.extend([str(x) for x in v if isinstance(x, (str, int, float))])
                elif isinstance(v, (str, int, float)):
                    possible_targets.append(str(v))
                # Ignore dicts or other unhashable types to prevent crash
        
        if possible_targets:
            # Check for direct match
            if self.main_stat in possible_targets:
                is_best = True
            # Special handling for Element DMG placeholder
            elif "属性ダメージアップ" in possible_targets and "ダメージアップ" in self.main_stat and self.main_stat != "通常攻撃ダメージアップ":
                is_best = True
            # Handle "Acceptable" cases like ATK% for Cost 3 attackers
            elif cost_prefix == "3" and self.main_stat == "攻撃力%" and any("ダメージアップ" in t or t == "属性ダメージアップ" for t in possible_targets):
                is_best = True
                consistency_msg = "攻撃力%は属性ダメージに次ぐ有力な選択肢です（許容範囲）"
                penalty = 0.97 # Slight penalty for not being "optimal"
            else:
                is_best = False
                target_str = " / ".join(set(possible_targets))
                consistency_msg = f"メインステータスが一致しません（理想：{target_str}）"
                penalty = 0.8

        achievement_rate *= penalty

        # Build Advice Generation (Gap to Ideal)
        advice_list = []
        ideal_stats = config_bundle.get("ideal_stats", {})
        
        if ideal_stats:
            # Get current estimated total stats (including echo)
            curr_crit_rate = estimated_stats.get(STAT_CRIT_RATE, 0)
            curr_crit_dmg = estimated_stats.get(STAT_CRIT_DMG, 0)
            # CRITICAL: Adjustment for Wuthering Waves (Display - 100%)
            adj_crit_dmg = max(0, curr_crit_dmg - 100.0)
            
            # 1. Crit Ratio Check (1:2)
            if curr_crit_rate > 5 and adj_crit_dmg > 5:
                if curr_crit_rate > 100.0:
                    effective_rate = 100.0
                    if curr_crit_rate > 105.0:
                        advice_list.append("会心率が100%を大きく超えています。過剰分を会心ダメージ等に振り分けましょう")
                else:
                    effective_rate = curr_crit_rate

                # Ideal DMG should be Rate * 2
                ideal_adj_dmg = effective_rate * 2.0
                if adj_crit_dmg < ideal_adj_dmg * 0.8:
                    advice_list.append("会心ダメージを優先的に稼ぐのが効率的です")
                elif effective_rate < (adj_crit_dmg / 2.0) * 0.8 and effective_rate < 100.0:
                    advice_list.append("会心率をもう少し上げると期待値が伸びます")

            # 2. Stat sufficiency check
            if STAT_ER in ideal_stats and STAT_ER in estimated_stats:
                if estimated_stats[STAT_ER] < ideal_stats[STAT_ER] * 0.9:
                    advice_list.append(f"{STAT_ER}が足りていません（目標: {ideal_stats[STAT_ER]}%）")
            
            if STAT_ATK_PERCENT in ideal_stats and STAT_ATK_PERCENT in estimated_stats:
                if estimated_stats[STAT_ATK_PERCENT] < ideal_stats[STAT_ATK_PERCENT] * 0.8:
                    advice_list.append(f"{STAT_ATK_PERCENT}を稼ぐとダメージが伸びます")

        return EvaluationResult(
            total_score=achievement_rate,
            effective_count=self.effective_stats_count,
            recommendation="rec_continue" if achievement_rate < 30.0 else "rec_use",
            rating=rating_key,
            individual_scores=results,
            estimated_stats=estimated,
            consistency_advice=consistency_msg,
            advice_list=advice_list
        )

    # --- Rating Logic ---

    def get_rating_by_achievement(self, rate: float, cost: str | int) -> str:
        """Determine rating key based on achievement rate and echo cost difficulty."""
        c = str(cost)
        if c == "3":
            # Cost 3 is harder to optimize
            if rate >= 80: return "rating_sss_single"
            if rate >= 65: return "rating_ss_single"
            if rate >= 45: return "rating_s_single"
            if rate >= 25: return "rating_a_single"
        elif c == "4":
            if rate >= 85: return "rating_sss_single"
            if rate >= 70: return "rating_ss_single"
            if rate >= 50: return "rating_s_single"
            if rate >= 30: return "rating_a_single"
        else: # Cost 1 or unknown
            if rate >= 90: return "rating_sss_single"
            if rate >= 75: return "rating_ss_single"
            if rate >= 55: return "rating_s_single"
            if rate >= 35: return "rating_a_single"

        return "rating_b_single" if rate >= 15 else "rating_c_single"

    def get_rating_normalized(self, score: float) -> str:
        """Evaluation for normalized score (Method 1)."""
        if score >= 70: return "rating_sss_norm"
        if score >= 50: return "rating_ss_norm"
        return "rating_s_norm" if score >= 30 else "rating_b_norm"

    def get_rating_ratio(self, score: float) -> str:
        """Evaluation for ratio score (Method 2)."""
        if score >= 75: return "rating_perf_ratio"
        if score >= 60: return "rating_exc_ratio"
        if score >= 45: return "rating_good_ratio"
        return "rating_avg_ratio" if score >= 30 else "rating_weak_ratio"

    def get_rating_roll(self, score: float) -> str:
        """Evaluation for roll quality (Method 3)."""
        if score >= 80: return "rating_god_roll"
        if score >= 65: return "rating_win_roll"
        return "rating_avg_roll" if score >= 45 else "rating_bad_roll"

    def get_rating_effective(self, score: float, eff_count: int) -> str | Tuple[str, ...]:
        """Evaluation for effective stats (Method 4)."""
        if eff_count >= 5 and score >= 70: return ("rating_perf_eff", score)
        if eff_count >= 4 and score >= 50: return ("rating_exc_eff", score)
        if eff_count >= 3 and score >= 30: return ("rating_good_eff", score)
        return ("rating_bad_eff", eff_count, score)

    def get_rating_cv(self, score: float) -> str:
        """Evaluation for Crit Value (Method 5)."""
        if score >= 45: return "rating_outstanding_cv"
        if score >= 38: return "rating_excellent_cv"
        if score >= 30: return "rating_good_cv"
        return "rating_acceptable_cv" if score >= 25 else "rating_weak_cv"

    def get_fingerprint(self) -> str:
        """Generate a unique MD5 hash based on echo statistics."""
        # Sort substats for consistent hashing
        subs_str = "|".join([f"{k}:{v}" for k, v in sorted(self.substats.items())])
        raw = f"{self.cost}|{self.main_stat}|{subs_str}"
        return hashlib.md5(raw.encode("utf-8")).hexdigest()

    def __str__(self) -> str:
        """Return a string representation of the Echo."""
        subs = "\n".join([f"  {n}: {v}" for n, v in self.substats.items()])
        return (
            f"Cost {self.cost} - Level {self.level}\n"
            f"Main: {self.main_stat}\n"
            f"Substats:\n{subs}\n"
            f"Achievement: {self.score:.2f}%"
        )