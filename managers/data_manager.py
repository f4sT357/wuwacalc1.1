import json
import os
import logging
from typing import Dict, Any, List

from utils.constants import (
    RES_GAME_DATA,
    RES_CALC_CONFIG,
)
from core.data_contracts import DataLoadError


class DataManager:
    """
    Manages loading and accessing external data configuration.
    """

    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.game_data_path = os.path.join(data_dir, RES_GAME_DATA)
        self.calc_config_path = os.path.join(data_dir, RES_CALC_CONFIG)

        self.game_data: Dict[str, Any] = {}
        self.calc_config: Dict[str, Any] = {}
        self.logger = logging.getLogger(__name__)
        self._alias_pairs_cache = None

    def load_all(self) -> None:
        """
        Loads both game data and calculation config.
        Raises DataLoadError if critical data cannot be loaded.
        """
        self.load_game_data()
        self.load_calc_config()
        self.validate_data()

    def validate_data(self) -> None:
        """
        Validates that loaded data contains essential keys.
        Raises:
            DataLoadError: If essential data is missing.
        """
        essential_game_keys = [
            "substat_max_values",
            "main_stat_options",
            "substat_types",
            "character_stat_weights",
            "tab_configs",
        ]

        for key in essential_game_keys:
            if key not in self.game_data:
                self.logger.critical(f"Missing essential key in game_data: {key}")
                raise DataLoadError(f"Corrupted game data: Missing '{key}'")

        essential_calc_keys = ["main_stat_multiplier", "roll_quality", "effective_stats", "cv_weights"]

        for key in essential_calc_keys:
            if key not in self.calc_config:
                self.logger.critical(f"Missing essential key in calc_config: {key}")
                raise DataLoadError(f"Corrupted calculation config: Missing '{key}'")

        self.logger.info("Data validation successful.")

    def load_game_data(self) -> None:
        """
        Loads game data from JSON.
        Raises:
            DataLoadError: If file is missing or invalid JSON.
        """
        if not os.path.exists(self.game_data_path):
            self.logger.critical(f"Game data file not found: {self.game_data_path}")
            raise DataLoadError(f"Game data file missing: {self.game_data_path}")

        try:
            with open(self.game_data_path, "r", encoding="utf-8") as f:
                self.game_data = json.load(f)
            self.logger.info(f"Loaded game data from {self.game_data_path}")
        except json.JSONDecodeError as e:
            self.logger.critical(f"Invalid JSON in game data: {e}")
            raise DataLoadError(f"Game data corrupted: {e}")
        except Exception as e:
            self.logger.critical(f"Failed to load game data: {e}")
            raise DataLoadError(f"Failed to load game data: {e}")

    def load_calc_config(self) -> None:
        """
        Loads calculation config from JSON.
        Raises:
            DataLoadError: If file is missing or invalid JSON.
        """
        if not os.path.exists(self.calc_config_path):
            self.logger.critical(f"Calculation config file not found: {self.calc_config_path}")
            raise DataLoadError(f"Config file missing: {self.calc_config_path}")

        try:
            with open(self.calc_config_path, "r", encoding="utf-8") as f:
                self.calc_config = json.load(f)
            self.logger.info(f"Loaded calculation config from {self.calc_config_path}")
        except json.JSONDecodeError as e:
            self.logger.critical(f"Invalid JSON in calculation config: {e}")
            raise DataLoadError(f"Calculation config corrupted: {e}")
        except Exception as e:
            self.logger.critical(f"Failed to load calculation config: {e}")
            raise DataLoadError(f"Failed to load calculation config: {e}")

    # --- Property Accessors for Convenience ---

    @property
    def substat_max_values(self) -> Dict[str, float]:
        val = self.game_data.get("substat_max_values", {})
        return val if isinstance(val, dict) else {}

    @property
    def main_stat_options(self) -> Dict[str, List[str]]:
        val = self.game_data.get("main_stat_options", {})
        return val if isinstance(val, dict) else {}

    @property
    def substat_types(self) -> Dict[str, str]:
        val = self.game_data.get("substat_types", {})
        return val if isinstance(val, dict) else {}

    @property
    def character_stat_weights(self) -> Dict[str, Dict[str, float]]:
        val = self.game_data.get("character_stat_weights", {})
        return val if isinstance(val, dict) else {}

    @property
    def character_main_stats(self) -> Dict[str, Dict[str, str]]:
        val = self.game_data.get("character_main_stats", {})
        return val if isinstance(val, dict) else {}

    @property
    def stat_aliases(self) -> Dict[str, List[str]]:
        return self.game_data.get("stat_aliases", {})

    @property
    def tab_configs(self) -> Dict[str, List[str]]:
        return self.game_data.get("tab_configs", {})

    @property
    def char_name_map_jp_to_en(self) -> Dict[str, str]:
        return self.game_data.get("char_name_map_jp_to_en", {})

    @property
    def main_stat_multiplier(self) -> float:
        return self.calc_config.get("main_stat_multiplier", 15.0)

    @property
    def roll_quality_config(self) -> Dict[str, Any]:
        return self.calc_config.get("roll_quality", {})

    @property
    def effective_stats_config(self) -> Dict[str, Any]:
        return self.calc_config.get("effective_stats", {})

    @property
    def cv_weights(self) -> Dict[str, float]:
        return self.calc_config.get("cv_weights", {})

    @property
    def character_config_map(self) -> Dict[str, str]:
        return self.game_data.get("character_config_map", {})

    def get_alias_pairs(self) -> List[tuple[str, str]]:
        """
        Returns a sorted list of (stat, alias) pairs for OCR matching.
        Aliases are sorted by length (descending) to ensure longest match first.
        """
        if self._alias_pairs_cache is not None:
            return self._alias_pairs_cache

        alias_pairs = []
        stat_aliases = self.stat_aliases
        for stat, aliases in stat_aliases.items():
            for alias in aliases:
                alias_pairs.append((stat, alias))

        # Sort by alias length descending
        alias_pairs.sort(key=lambda x: -len(x[1]))
        self._alias_pairs_cache = alias_pairs
        return alias_pairs
