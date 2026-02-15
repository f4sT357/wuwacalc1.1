"""
Application Setup Module

Responsible for initializing and wiring together the various managers and logic modules.
"""

import sys
import os
from typing import Any
from PySide6.QtWidgets import QMessageBox, QTabWidget

from managers.config_manager import ConfigManager
from managers.data_manager import DataManager
from managers.character_manager import CharacterManager
from managers.history_manager import HistoryManager
from managers.theme_manager import ThemeManager
from managers.tab_manager import TabManager
from core.score_calculator import ScoreCalculator
from core.image_processor import ImageProcessor
from core.app_logic import AppLogic
from ui.html_renderer import HtmlRenderer
from ui.ui_components import UIComponents
from utils.constants import DIR_DATA, CONFIG_FILENAME
from utils.utils import get_app_path, get_resource_path
from utils.logger import logger


class AppContext:
    """Container for all application-wide managers and logic."""

    def __init__(self, main_window: Any):
        self.main_window = main_window
        self.logger = logger

        # 1. Data & Config
        try:
            self.data_manager = DataManager(get_resource_path(DIR_DATA))
            self.data_manager.load_all()
        except Exception as e:
            self.logger.critical(f"Failed to initialize DataManager: {e}")
            QMessageBox.critical(None, "Data Load Error", f"Critical game data could not be loaded.\nError: {e}")
            sys.exit(1)

        config_path = os.path.join(get_app_path(), CONFIG_FILENAME)
        self.config_manager = ConfigManager(config_path)
        load_status = self.config_manager.load()
        if load_status == "CORRUPTED":
            self.logger.warning("Config file is corrupted. Using default settings.")
            QMessageBox.warning(
                None,
                "Config Load Warning",
                f"The configuration file at {config_path} is corrupted and could not be loaded.\n"
                "Standard settings will be used instead.",
            )

        self.app_config = self.config_manager.get_app_config()

        # 2. Basic Managers
        self.character_manager = CharacterManager(self.logger, self.data_manager)
        self.history_mgr = HistoryManager()
        self.theme_manager = ThemeManager(main_window)

        # 3. UI Framework
        self.notebook = QTabWidget()
        self.ui = UIComponents(main_window)

        # 4. Logic Modules
        self.html_renderer = HtmlRenderer(
            main_window.tr,
            self.app_config.language,
            self.app_config.text_color,
        )
        self.score_calc = ScoreCalculator(
            self.data_manager, self.character_manager, self.history_mgr, self.html_renderer, self.config_manager
        )
        self.tab_mgr = TabManager(
            self.data_manager, self.config_manager, main_window.tr, self.character_manager
        )
        self.logic = AppLogic(main_window.tr, self.data_manager, self.config_manager)
        self.image_proc = ImageProcessor(self.logic, self.config_manager)
