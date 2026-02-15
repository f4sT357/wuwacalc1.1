"""
Score Calculation Module (PySide6)

Provides the logic for calculating Echo scores based on character profiles 
and game data.
"""

from __future__ import annotations

from typing import Dict, Any, Optional, TYPE_CHECKING
from PySide6.QtCore import QObject, Signal

from core.echo_data import EchoData
from core.data_contracts import EchoEntry, EvaluationResult
from utils.constants import ACTION_SINGLE, ACTION_BATCH

if TYPE_CHECKING:
    from ui.html_renderer import HtmlRenderer


class ScoreCalculator(QObject):
    """
    Class responsible for score calculation logic.
    
    This class is decoupled from UI components and communicates 
    via signals.
    """

    # Signals for communication with UI
    log_requested = Signal(str)
    error_occurred = Signal(str, str)
    single_calculation_completed = Signal(str, str, object)  # html, tab_name, evaluation
    batch_calculation_completed = Signal(str, str)  # html, character_name

    def __init__(
        self,
        data_manager: Any,
        character_manager: Any,
        history_manager: Any,
        renderer: HtmlRenderer,
        config_manager: Any,
    ):
        """
        Initialize the score calculator with its dependencies.
        """
        super().__init__()
        self.data_manager = data_manager
        self.character_manager = character_manager
        self.history_mgr = history_manager
        self.renderer = renderer
        self.config_manager = config_manager

    def calculate_single(
        self, 
        character: str, 
        tab_name: str, 
        entry: EchoEntry, 
        enabled_methods: Dict[str, bool]
    ) -> None:
        """
        Perform evaluation for a single echo and emit result. 
        
        Args:
            character: Internal name of the character.
            tab_name: Name of the UI tab being evaluated.
            entry: Data object containing echo stats.
            enabled_methods: Dict of calculation methods to include.
        """
        try:
            if not entry.main_stat:
                self.log_requested.emit(
                    f"The main stat for {tab_name} is not entered."
                )
                return

            weights = self.character_manager.get_stat_weights(character)
            config_bundle = self._get_config_bundle()
            config_bundle["character_main_stats"] = self.character_manager.get_main_stats(character)

            evaluation = self._process_echo_evaluation(
                entry, weights, config_bundle, enabled_methods, 
                character, ACTION_SINGLE, tab_name
            )

            if evaluation:
                # Comparison logic with equipped echo
                equipped = self.character_manager.get_equipped_echo(character, tab_name)
                if equipped:
                    eq_eval = self._process_echo_evaluation(
                        equipped, weights, config_bundle, enabled_methods,
                        character, "INTERNAL", tab_name, record_history=False
                    )
                    if eq_eval:
                        evaluation.comparison_diff = (
                            evaluation.total_score - eq_eval.total_score
                        )

                substats = self.extract_substats_from_entry(entry)
                echo = EchoData(entry.cost, entry.main_stat, substats)

                html = self.renderer.render_single_score(
                    character, tab_name, entry, entry.main_stat, echo, evaluation
                )

                self.single_calculation_completed.emit(html, tab_name, evaluation)
                self.log_requested.emit(
                    f"Individual evaluation for {tab_name} complete."
                )

        except Exception as e:
            error_msg = f"Individual score calculation error: {e}"
            self.log_requested.emit(error_msg)
            self.error_occurred.emit("Error", error_msg)

    def calculate_batch(
        self, 
        character: str, 
        tabs_data: Dict[str, EchoEntry], 
        enabled_methods: Dict[str, bool], 
        language: str
    ) -> None:
        """
        Perform evaluation for all echoes in batch and emit combined result.
        
        Args:
            character: Internal name of the character.
            tabs_data: Mapping of tab names to EchoEntry objects.
            enabled_methods: Dict of calculation methods to include.
            language: Current UI language code.
        """
        try:
            weights = self.character_manager.get_stat_weights(character)
            config_bundle = self._get_config_bundle()
            config_bundle["character_main_stats"] = self.character_manager.get_main_stats(character)

            all_evaluations = []
            total_scores = {"total": 0.0}
            
            # Initialize method accumulators
            for method in ["normalized", "ratio", "roll", "effective", "cv"]:
                if enabled_methods.get(method, False):
                    total_scores[method] = 0.0

            calculated_count = 0
            for tab_name, entry in tabs_data.items():
                if not entry or not entry.main_stat:
                    continue

                evaluation = self._process_echo_evaluation(
                    entry, weights, config_bundle, enabled_methods, 
                    character, ACTION_BATCH, tab_name
                )

                if evaluation:
                    eval_data = self._format_eval_data_for_batch(
                        tab_name, evaluation, language
                    )
                    all_evaluations.append(eval_data)
                    total_scores["total"] += evaluation.total_score
                    for method, score in evaluation.individual_scores.items():
                        if method in total_scores:
                            total_scores[method] += score
                    calculated_count += 1

            if calculated_count == 0:
                self.batch_calculation_completed.emit("No data available.\n", character)
            else:
                html = self.renderer.render_batch_score(
                    character, calculated_count, len(tabs_data), 
                    all_evaluations, total_scores, enabled_methods
                )
                self.batch_calculation_completed.emit(html, character)
                self.log_requested.emit(
                    f"Batch calculation complete ({calculated_count} echoes)."
                )

        except Exception as e:
            error_msg = f"Batch calculation error: {e}"
            self.log_requested.emit(error_msg)
            self.error_occurred.emit("Error", error_msg)

    def extract_substats_from_entry(self, entry: EchoEntry) -> Dict[str, float]:
        """
        Extract substats from EchoEntry with robust validation. 
        
        Returns:
            Dictionary mapping stat names to float values.
        """
        substats = {}
        if not entry or not entry.substats:
            return substats

        for sub in entry.substats:
            if not sub.stat or not sub.value:
                continue
            try:
                # Clean value of common OCR or manual noise
                clean_val = (
                    sub.value.replace("%", "")
                    .replace(" ", "").replace("+", "").strip()
                )
                if not clean_val:
                    continue
                
                val = float(clean_val)
                # Safeguard against unreasonable values
                if not (0 <= val < 1000000):
                     self.log_requested.emit(
                         f"Value out of range for '{self.renderer.tr(sub.stat)}': '{val}'"
                     )
                     continue

                substats[sub.stat] = val
            except (ValueError, TypeError):
                self.log_requested.emit(
                    f"Invalid numeric value for '{self.renderer.tr(sub.stat)}': '{sub.value}'"
                )
                continue
        return substats

    def _get_config_bundle(self) -> Dict[str, Any]:
        """Create a configuration bundle for EchoData from DataManager."""
        dm = self.data_manager
        return {
            "substat_max_values": dm.substat_max_values,
            "main_stat_multiplier": dm.main_stat_multiplier,
            "roll_quality": dm.roll_quality_config,
            "effective_stats": dm.effective_stats_config,
            "cv_weights": dm.cv_weights,
        }

    def _process_echo_evaluation(
        self,
        entry: EchoEntry,
        weights: Dict[str, float],
        config_bundle: Dict[str, Any],
        enabled_methods: Dict[str, bool],
        character: str,
        action_type: str,
        tab_name_for_log: str,
        record_history: bool = True,
    ) -> Optional[EvaluationResult]:
        """
        Internal core logic for evaluating an echo entry.
        
        Calculates score, detects duplicates, and records history.
        """
        if not entry.main_stat:
            return None

        substats = self.extract_substats_from_entry(entry)
        if record_history:
            self.log_requested.emit(
                f"Evaluating Echo - Cost: {entry.cost}, Main: "
                f"{entry.main_stat}, Substats: {substats}"
            )

        echo = EchoData(entry.cost, entry.main_stat, substats)

        # Retrieve character profile for advanced calculation parameters
        profile = self.character_manager.get_character_profile(character)
        stat_offsets = profile.stat_offsets if profile else {}
        base_stats = profile.base_stats if profile else {}
        ideal_stats = profile.ideal_stats if profile else {}
        scaling_stat = profile.scaling_stat if profile else "攻撃力"

        # Duplicate detection using history
        fingerprint = echo.get_fingerprint()
        if record_history:
            duplicates = self.history_mgr.find_duplicates(fingerprint)
            if duplicates:
                self.log_requested.emit(
                    f"[{tab_name_for_log}] Duplicate Detected "
                    f"(Previous IDs: {duplicates})"
                )

        # Core calculation
        evaluation = echo.evaluate_comprehensive(
            weights,
            config_bundle,
            enabled_methods,
            stat_offsets=stat_offsets,
            base_stats=base_stats,
            ideal_stats=ideal_stats,
            scaling_stat=scaling_stat,
        )

        # Record result to history database
        if record_history:
            result_summary = f"Score: {evaluation.total_score:.2f} ({evaluation.rating})"
            app_config = self.config_manager.get_app_config()
            self.history_mgr.add_entry(
                character=character,
                cost=entry.cost or "Unknown",
                action=action_type,
                result=result_summary,
                fingerprint=fingerprint,
                details={
                    "score": evaluation.total_score, 
                    "rating_key": evaluation.rating
                },
                duplicate_mode=app_config.history_duplicate_mode,
            )

        return evaluation

    def _format_eval_data_for_batch(
        self, tab_name: str, evaluation: EvaluationResult, language: str
    ) -> Dict[str, Any]:
        """Format an evaluation result for batch rendering display."""
        from utils.languages import TRANSLATIONS

        lang_dict = TRANSLATIONS.get(language, TRANSLATIONS["en"])

        eval_data = {
            "tab_name": tab_name,
            "effective_count": evaluation.effective_count,
            "total": evaluation.total_score,
            "recommendation": lang_dict.get(
                evaluation.recommendation, evaluation.recommendation
            ),
        }

        for method, score in evaluation.individual_scores.items():
            eval_data[method] = score

        return eval_data