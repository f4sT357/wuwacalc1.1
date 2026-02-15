"""
Configuration Management Module

A module for centrally managing application settings.
Provides unified access for loading, saving, and accessing settings.
"""

import json
import os
import logging
from dataclasses import dataclass, asdict, field, fields
from typing import Dict, Any
from utils.constants import (
    DEFAULT_COST_CONFIG,
    DEFAULT_WINDOW_WIDTH,
    DEFAULT_WINDOW_HEIGHT,
    IMAGE_PREVIEW_MAX_WIDTH,
    IMAGE_PREVIEW_MAX_HEIGHT,
)

logger = logging.getLogger(__name__)


@dataclass
class UIConfig:
    """UI dimensions and layout settings."""

    window_width: int = DEFAULT_WINDOW_WIDTH
    window_height: int = DEFAULT_WINDOW_HEIGHT
    right_top_height: int = 600
    log_min_height: int = 100
    log_default_height: int = 150
    image_preview_max_width: int = IMAGE_PREVIEW_MAX_WIDTH
    image_preview_max_height: int = IMAGE_PREVIEW_MAX_HEIGHT


@dataclass
class AppConfig:
    language: str = "ja"
    theme: str = "dark"
    app_font: str = ""
    current_config_key: str = DEFAULT_COST_CONFIG
    character_var: str = ""
    auto_apply_main_stats: bool = True
    auto_calculate: bool = False
    mode_var: str = "manual"
    score_mode_var: str = "batch"
    crop_mode: str = "percent"
    crop_left_percent: float = 30.0
    crop_top_percent: float = 30.0
    crop_width_percent: float = 35.0
    crop_height_percent: float = 40.0
    text_color: str = "#ffffff"
    custom_input_bg_color: str = ""
    accent_mode: str = "auto"  # "auto" (element-based) or "custom"
    custom_accent_color: str = "#FFD700"  # Gold
    # OCR
    ocr_engine: str = "pillow"  # Standard engine
    skip_duplicate_ocr: bool = True  # New setting for input skipping

    transparent_frames: bool = False
    show_text_shadow: bool = True
    text_shadow_color: str = "#000000"
    shadow_offset_x: float = 2.0
    shadow_offset_y: float = 2.0
    shadow_blur: float = 5.0
    shadow_spread: float = 0.0
    history_duplicate_mode: str = "latest"  # Options: "all", "latest", "oldest"
    enabled_calc_methods: dict = field(
        default_factory=lambda: {
            "normalized": True,
            "ratio": True,
            "roll": True,
            "effective": False,
            "cv": False,
        }
    )
    background_opacity: float = 0.9

    def __post_init__(self):
        pass

    def validate(self) -> bool:
        """Validate the setting values.

        Returns:
            True: All settings are valid, False: There are invalid settings.
        """
        # Validate language setting
        if self.language not in ["ja", "en", "zh-CN"]:
            logger.warning(f"Invalid language: {self.language}, using 'en'")
            self.language = "en"

        # Validate crop settings (0-100%)
        if not (0 <= self.crop_top_percent <= 100):
            logger.warning(f"Invalid crop_top_percent: {self.crop_top_percent}, resetting to 0")
            self.crop_top_percent = 0.0

        if not (0 <= self.crop_left_percent <= 100):
            logger.warning(f"Invalid crop_left_percent: {self.crop_left_percent}, resetting to 0")
            self.crop_left_percent = 0.0

        if not (0 <= self.crop_width_percent <= 100):
            logger.warning(f"Invalid crop_width_percent: {self.crop_width_percent}, resetting to 30")
            self.crop_width_percent = 30.0

        if not (0 <= self.crop_height_percent <= 100):
            logger.warning(f"Invalid crop_height_percent: {self.crop_height_percent}, resetting to 40")
            self.crop_height_percent = 40.0

        # Validate crop mode
        if self.crop_mode not in ["drag", "percent"]:
            logger.warning(f"Invalid crop_mode: {self.crop_mode}, using 'drag'")
            self.crop_mode = "drag"

        # Validate input mode
        if self.mode_var not in ["manual", "ocr"]:
            logger.warning(f"Invalid mode_var: {self.mode_var}, using 'manual'")
            self.mode_var = "manual"

        # Validate calculation mode
        if self.score_mode_var not in ["batch", "single"]:
            logger.warning(f"Invalid score_mode_var: {self.score_mode_var}, using 'batch'")
        if self.score_mode_var not in ["batch", "single"]:
            logger.warning(f"Invalid score_mode_var: {self.score_mode_var}, using 'batch'")
            self.score_mode_var = "batch"

        # Validate enabled calculation methods
        if not isinstance(self.enabled_calc_methods, dict):
            logger.warning("Invalid enabled_calc_methods type, resetting to defaults")
            self.enabled_calc_methods = {"normalized": True, "ratio": True, "roll": True, "effective": True, "cv": True}
        else:
            # Ensure all method keys exist
            default_methods = {"normalized", "ratio", "roll", "effective", "cv"}
            for method in default_methods:
                if method not in self.enabled_calc_methods:
                    self.enabled_calc_methods[method] = True

            # Ensure at least one method is enabled
            if not any(self.enabled_calc_methods.values()):
                logger.warning("No calculation methods enabled, enabling all methods")
                for method in self.enabled_calc_methods:
                    self.enabled_calc_methods[method] = True

        # Validate background opacity
        if not (0.0 <= self.background_opacity <= 1.0):
            logger.warning(f"Invalid background_opacity: {self.background_opacity}, resetting to 0.9")
            self.background_opacity = 0.9

        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format (without expanding UI settings)."""
        data = asdict(self)
        # Keep UIConfig nested
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AppConfig":
        """Create AppConfig from a dictionary, ignoring unknown fields."""
        app_fields = {f.name for f in fields(cls)}

        # Create AppConfig with known fields from the root of data
        filtered_app_data = {k: v for k, v in data.items() if k in app_fields}
        config = cls(**filtered_app_data)

        # Handle UIConfig separately and attach it to the config instance
        ui_data = data.get("ui", {})
        if isinstance(ui_data, dict):
            ui_fields = {f.name for f in fields(UIConfig)}
            filtered_ui_data = {k: v for k, v in ui_data.items() if k in ui_fields}
            config.ui = UIConfig(**filtered_ui_data)
        else:
            config.ui = UIConfig()

        # Run validation after creation
        config.validate()
        return config


class ConfigManager:
    """Configuration management class.

    Manages application and UI settings,
    and provides file saving and loading.
    """

    def __init__(self, config_path: str):
        """
        Args:
            config_path: Path to the configuration file.
        """
        self.config_path = config_path
        self.config = AppConfig()
        self.config.ui = UIConfig()

    def load(self) -> bool:
        """Load from the configuration file.

        Returns:
            True: Load successful, False: File does not exist or load failed.
        """
        if not os.path.exists(self.config_path):
            logger.info(f"Configuration file not found. Using default settings: {self.config_path}")
            return False

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Backward compatibility: Convert from old (flat) to new (nested) format
            if "ui" not in data:
                # Extract UI settings from the flat structure
                ui_keys = {
                    "window_width",
                    "window_height",
                    "right_top_height",
                    "log_min_height",
                    "log_default_height",
                    "image_preview_max_width",
                    "image_preview_max_height",
                }
                ui_data = {k: data.pop(k) for k in ui_keys if k in data}
                if ui_data:
                    data["ui"] = ui_data

            self.config = AppConfig.from_dict(data)
            logger.info(f"Settings loaded from: {self.config_path}")
            return True

        except json.JSONDecodeError as e:
            msg = f"JSON parsing error in configuration file: {e}"
            logger.error(msg)
            # Signal that the file exists but is corrupted
            return "CORRUPTED"
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
            return False

    def save(self) -> bool:
        """Save settings to a file.

        Returns:
            True: Save successful, False: Save failed.
        """
        try:
            # Validate before saving
            self.config.validate()

            # Create directory if it does not exist
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)

            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config.to_dict(), f, ensure_ascii=False, indent=2)

            logger.debug(f"Settings saved to: {self.config_path}")
            return True

        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            return False

    def get_app_config(self) -> AppConfig:
        """Get application settings.

        Returns:
            AppConfig instance.
        """
        return self.config

    def get_ui_config(self) -> UIConfig:
        """Get UI settings.

        Returns:
            UIConfig instance.
        """
        return self.config.ui

    def update_app_setting(self, key: str, value: Any) -> None:
        """Update an application setting.

        Args:
            key: The setting key.
            value: The setting value.
        """
        if hasattr(self.config, key):
            setattr(self.config, key, value)
        else:
            logger.warning(f"Unknown setting key: {key}")

    def update_ui_setting(self, key: str, value: Any) -> None:
        """Update a UI setting.

        Args:
            key: The setting key.
            value: The setting value.
        """
        if hasattr(self.config.ui, key):
            setattr(self.config.ui, key, value)
        else:
            logger.warning(f"Unknown UI setting key: {key}")
