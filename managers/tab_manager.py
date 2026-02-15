"""
Tab Management Module (PySide6)

Handles the lifecycle of echo tabs, including data synchronization, 
OCR application, and result storage.
"""

from __future__ import annotations

import logging
import hashlib
from typing import Dict, Any, List, Optional, Callable, TYPE_CHECKING

from PySide6.QtWidgets import QTabWidget, QFileDialog, QWidget
from PySide6.QtCore import QObject, Signal

from core.data_contracts import EchoEntry, OCRResult
from utils.constants import DEFAULT_COST_CONFIG
from ui.widgets.echo_tab import EchoTabWidget

if TYPE_CHECKING:
    from PIL import Image
    from managers.config_manager import ConfigManager
    from managers.data_manager import DataManager
    from managers.character_manager import CharacterManager
    from core.score_calculator import ScoreCalculator

class TabImageData:
    """Container for original and cropped images associated with a tab."""
    def __init__(self, original: Image.Image, cropped: Image.Image):
        self.original = original
        self.cropped = cropped


class TabResultData:
    """Container for the HTML calculation result associated with a tab."""
    def __init__(self, content: str):
        self.content = content


class TabManager(QObject):
    """
    Manager class for handling echo tabs and their associated data.
    
    This class is decoupled from the main application window and 
    communicates primarily via signals.
    """

    # Signals for UI notifications
    log_requested = Signal(str)
    tabs_rebuild_requested = Signal(str, list)  # config_key, tab_names
    tab_label_update_requested = Signal(int, str)
    image_preview_requested = Signal(object)  # Image.Image
    calculation_requested = Signal()
    tabs_updated = Signal()

    def __init__(
        self, 
        data_manager: DataManager, 
        config_manager: ConfigManager, 
        tr_func: Callable, 
        character_manager: CharacterManager
    ):
        """Initialize the TabManager with required dependencies."""
        super().__init__()
        self.data_manager = data_manager
        self.config_manager = config_manager
        self.tr = tr_func
        self.character_manager = character_manager

        self.logger = logging.getLogger(__name__)
        self.tabs_content = {}
        self._updating_tabs = False

        # State storage: mapping tab_name -> data object
        self._tab_images: Dict[str, TabImageData] = {}
        self._tab_results: Dict[str, TabResultData] = {}

    def get_selected_tab_name(self, current_index: int) -> Optional[str]:
        """Return the internal name of the currently selected tab."""
        if current_index == -1:
            return None

        config_key = self.config_manager.get_app_config().current_config_key
        tab_configs = self.data_manager.tab_configs
        if config_key in tab_configs:
            keys = tab_configs[config_key]
            if current_index < len(keys):
                return keys[current_index]
        return None

    def clear_tab(self, tab_name: str) -> None:
        """Clear all data and images for a specific tab."""
        try:
            if not tab_name or tab_name not in self.tabs_content:
                return

            content = self.tabs_content[tab_name]
            content["widget"].clear_data()

            self._tab_images.pop(tab_name, None)
            self._tab_results.pop(tab_name, None)

            self.log_requested.emit(f"Cleared contents of tab '{tab_name}'.")
        except Exception as e:
            msg = f"Failed to clear tab: {e}"
            self.log_requested.emit(msg)
            self.logger.exception(msg)

    def clear_all(self) -> None:
        """Clear data for all tabs and reset internal storage."""
        try:
            for content in self.tabs_content.values():
                content["widget"].clear_data()

            self._tab_images.clear()
            self._tab_results.clear()
            self.log_requested.emit("All echo tabs have been cleared.")
        except Exception as e:
            self.log_requested.emit(f"Failed to reset items: {e}")
            self.logger.exception("Clear all error")

    def update_tabs(self) -> None:
        """Rebuild the UI tabs based on the current cost configuration."""
        self._updating_tabs = True
        try:
            config_key = self._validate_config_key()
            config_tab_names = self.data_manager.tab_configs[config_key]

            # Save existing data to restore after rebuild
            old_data = self._save_current_tab_state()

            self.tabs_content = {}
            self.tabs_rebuild_requested.emit(config_key, config_tab_names)

            # Note: The UI layer is expected to call register_tab_widget during rebuild
            cost_counts = self._calculate_cost_counts(config_tab_names)
            current_cost_indices = {}

            # We need to wait for or ensure widgets are registered before restoring
            # In this signal-driven approach, we might need a separate step for restoration
            # if registration is asynchronous. For now, assume synchronous signal handling.
            
            # (Logic for restoration might need to be triggered after UI confirms rebuild)
            self._temp_old_data = old_data # Store temporarily
            
        except Exception as e:
            self.log_requested.emit(f"Tab update error: {e}")
            self.logger.exception("Tab update failed")
        finally:
            self._updating_tabs = False

    def register_tab_widget(self, tab_name: str, widget: EchoTabWidget, cost_num: str, cost_key: str) -> None:
        """Register a widget for a logical tab slot."""
        self.tabs_content[tab_name] = {
            "cost": cost_num,
            "cost_key": cost_key,
            "widget": widget
        }
        
        # If we have pending data to restore for this tab, do it now
        if hasattr(self, "_temp_old_data"):
            cost_counts = self._calculate_cost_counts(self.tabs_content.keys())
            # This is tricky because we need the index. 
            # Re-evaluating: It's better if the UI calls a 'complete_rebuild' method.
            pass

    def finalize_rebuild(self) -> None:
        """Called by UI after all tab widgets have been registered."""
        if not hasattr(self, "_temp_old_data"):
            self.tabs_updated.emit()
            return
            
        config_key = self._validate_config_key()
        tab_names = self.data_manager.tab_configs[config_key]
        cost_counts = self._calculate_cost_counts(tab_names)
        current_cost_indices = {}

        for tab_name in tab_names:
            cost_num = next((ch for ch in tab_name if ch.isdigit()), "1")
            current_idx = current_cost_indices.get(cost_num, 0) + 1
            current_cost_indices[cost_num] = current_idx
            
            state_key = (cost_num, current_idx)
            if state_key in self._temp_old_data:
                self._restore_tab_data(tab_name, self._temp_old_data[state_key])
        
        del self._temp_old_data
        self.tabs_updated.emit()

    def retranslate_tabs(self, language: str) -> None:
        """Update tab labels and widget text for the specified language."""
        self._updating_tabs = True
        try:
            config_key = self._validate_config_key()
            tab_names = self.data_manager.tab_configs.get(config_key, [])
            for i, name in enumerate(tab_names):
                new_label = self._generate_tab_label(name)
                self.tab_label_update_requested.emit(i, new_label)

            for content in self.tabs_content.values():
                content["widget"].retranslate()
                self.apply_character_main_stats()
        finally:
            self._updating_tabs = False

    def _validate_config_key(self) -> str:
        """Ensure the current config key exists in game data."""
        config_key = self.config_manager.get_app_config().current_config_key
        if config_key not in self.data_manager.tab_configs:
            config_key = DEFAULT_COST_CONFIG
        return config_key

    def _save_current_tab_state(self) -> Dict[tuple, Any]:
        """Capture the current data in all tabs before a UI rebuild."""
        state = {}
        cost_indices = {}
        for tab_name, content in self.tabs_content.items():
            cost_num = content.get("cost", "1")
            idx = cost_indices.get(cost_num, 0) + 1
            cost_indices[cost_num] = idx
            state_key = (cost_num, idx)

            main_val, substats = content["widget"].get_data()
            sub_vals = [(s.stat, s.value) for s in substats]

            state[state_key] = {"main_stat": main_val, "substats": sub_vals}
        return state

    def _calculate_cost_counts(self, tab_names: List[str]) -> Dict[str, int]:
        """Count how many of each cost type are in the current configuration."""
        totals = {}
        for name in tab_names:
            first_digit = next((ch for ch in name if ch.isdigit()), None)
            if first_digit:
                totals[first_digit] = totals.get(first_digit, 0) + 1
        return totals

    def _create_and_add_tab_page(self, tab_name: str, cost_num: str, cost_key: str) -> None:
        """Create a new EchoTabWidget and add it to the notebook."""
        main_opts = self.data_manager.main_stat_options.get(
            cost_num, ["HP", "ATK", "DEF"]
        )
        sub_opts = list(self.data_manager.substat_max_values.keys())

        tab_widget = EchoTabWidget(cost_num, main_opts, sub_opts, self.tr)
        tab_label = self._generate_tab_label(tab_name)
        self.notebook.addTab(tab_widget, tab_label)

        self.tabs_content[tab_name] = {
            "cost": cost_num, 
            "cost_key": cost_key, 
            "widget": tab_widget
        }


    def _generate_tab_label(self, tab_name: str) -> str:
        """Generate a translated display label for a tab."""
        try:
            parts = tab_name.split("_")
            c_num = parts[0]
            base_label = self.tr("cost_echo", c_num)
            suffix = f" {parts[1]}" if len(parts) >= 2 else ""
            return f"{base_label}{suffix}"
        except Exception:
            return tab_name

    def _restore_tab_data(self, tab_name: str, data: Dict[str, Any]) -> None:
        """Populate a tab widget with stored data."""
        if tab_name not in self.tabs_content:
            return
        content = self.tabs_content[tab_name]
        main_val = data.get("main_stat", "")
        saved_substats = data.get("substats", [])
        content["widget"].set_data(main_val, saved_substats)

    def extract_tab_data(self, tab_name: str) -> Optional[EchoEntry]:
        """Retrieve structured echo data from a specific tab widget."""
        if tab_name not in self.tabs_content:
            return None
        content = self.tabs_content[tab_name]
        main_stat, substats = content["widget"].get_data()
        cost = content.get("cost")
        return EchoEntry(tab_index=0, cost=cost, main_stat=main_stat, substats=substats)

    def get_all_echo_entries(self) -> List[EchoEntry]:
        """Retrieve echo data from all active tabs."""
        entries = []
        for tab_name in self.tabs_content:
            entry = self.extract_tab_data(tab_name)
            if entry:
                entries.append(entry)
        return entries

    @staticmethod
    def find_duplicate_entries(entries: List[EchoEntry]) -> List[int]:
        """Identify indices of echoes with identical cost, main, and substats."""
        seen = {}
        duplicates = []
        for idx, entry in enumerate(entries):
            # Skip empty entries for duplicate detection
            if not entry.main_stat and not entry.substats:
                continue
                
            substats_tuple = tuple((s.stat, s.value) for s in entry.substats)
            key = (entry.cost, entry.main_stat, substats_tuple)
            if key in seen:
                duplicates.append(idx)
            else:
                seen[key] = idx
        return duplicates

    def apply_character_main_stats(self, force: bool = False, character: str = None) -> None:
        """Apply preferred main stats to tabs based on character profile."""
        if not character:
            character = self.config_manager.get_app_config().character_var
        if not character:
            return
        if not force and not self.config_manager.get_app_config().auto_apply_main_stats:
            return

        mainstats = self.character_manager.get_main_stats(character)
        if not mainstats:
            return

        for tab_name, content in self.tabs_content.items():
            cost_num = str(content.get("cost", "1"))
            base_opts = self.data_manager.main_stat_options.get(
                cost_num, ["HP", "ATK", "DEF"]
            )

            preferred = []
            pref_val = mainstats.get(tab_name) or mainstats.get(cost_num)
            if pref_val:
                preferred = pref_val if isinstance(pref_val, list) else [pref_val]

            # Re-order options: preferred first
            final_opts = preferred if preferred else base_opts
            content["widget"].update_main_options(final_opts, preferred)

    def find_best_tab_match(
        self, cost: str, main_stat: str, character: str = None
    ) -> Optional[str]:
        """Find the most logical tab to place new data based on cost and main stat."""
        if not cost:
            return None
        config_key = self._validate_config_key()
        tab_names = self.data_manager.tab_configs.get(config_key, [])
        mainstats_pref = (self.character_manager.get_main_stats(character) 
                          if character else {})

        cost_matches = [
            n for n in tab_names 
            if self.tabs_content.get(n) and self.tabs_content[n]["cost"] == str(cost)
        ]

        if not cost_matches:
            return None

        # Prefer empty tabs first
        empty_tabs = [n for n in cost_matches if self.tabs_content[n]["widget"].is_empty()]

        if empty_tabs:
            if character:
                for name in empty_tabs:
                    pref = mainstats_pref.get(name) or mainstats_pref.get(str(cost))
                    if pref:
                        p_list = pref if isinstance(pref, list) else [pref]
                        if main_stat in p_list:
                            return name
            return empty_tabs[0]

        # Fallback to occupied tabs matching preference
        if character:
            for name in cost_matches:
                pref = mainstats_pref.get(name) or mainstats_pref.get(str(cost))
                if pref:
                    p_list = pref if isinstance(pref, list) else [pref]
                    if main_stat in p_list:
                        return name

        return cost_matches[0]
    
    def get_next_available_tab(self, exclude_tabs: List[str] = None, cost: str = None) -> Optional[str]:
        """Find the first empty tab that is not in the excluded list, optionally filtered by cost."""
        if exclude_tabs is None:
            exclude_tabs = []
            
        config_key = self._validate_config_key()
        tab_names = self.data_manager.tab_configs.get(config_key, [])
        
        # 1. Look for empty tabs with matching cost
        for name in tab_names:
            if name not in exclude_tabs and self.is_tab_empty(name):
                if cost is None or self.tabs_content[name]["cost"] == str(cost):
                    return name
        
        # 2. If no matching empty tab, try to find ANY tab (even occupied) that matches cost 
        #    and isn't in exclusion (for fallback)
        if cost is not None:
            for name in tab_names:
                if name not in exclude_tabs and self.tabs_content[name]["cost"] == str(cost):
                    return name

        # 3. Final fallback: just return the first one not in exclusion if any (without cost constraint)
        for name in tab_names:
            if name not in exclude_tabs:
                return name
                
        return None

    def is_tab_empty(self, tab_name: str) -> bool:
        """Check if a specific tab has no data entered."""
        if tab_name not in self.tabs_content:
            return True
        return self.tabs_content[tab_name]["widget"].is_empty()

    def has_calculatable_data(self, mode: str = "batch", current_index: int = -1) -> bool:
        """Check if there is enough data (at least one substat) to trigger a calculation."""
        if mode == "single":
            name = self.get_selected_tab_name(current_index)
            return name is not None and self.has_substats(name)
        
        return any(self.has_substats(n) for n in self.tabs_content)

    def has_substats(self, tab_name: str) -> bool:
        """Check if a specific tab has any substat data entered."""
        if tab_name not in self.tabs_content:
            return False
        return self.tabs_content[tab_name]["widget"].has_substats()

    def load_entry_into_tab(self, tab_name: str, entry: EchoEntry) -> None:
        """Load an EchoEntry object into a specific tab widget."""
        if tab_name not in self.tabs_content:
            return

        content = self.tabs_content[tab_name]
        sub_vals = [(s.stat, s.value) for s in entry.substats]
        content["widget"].set_data(entry.main_stat, sub_vals)
        
        self.log_requested.emit(
            f"[{tab_name}] Loaded echo (Cost {entry.cost}, Main: {entry.main_stat})"
        )

        self._tab_images.pop(tab_name, None)
        self._tab_results.pop(tab_name, None)

    def apply_ocr_result_to_tab(self, tab_name: str, result: OCRResult) -> None:
        """Apply OCR results to a tab, comparing against existing data if needed."""
        if tab_name not in self.tabs_content:
            return

        content = self.tabs_content[tab_name]
        character = self.config_manager.get_app_config().character_var
        
        # 1. Duplicate Check
        current_entry = self.extract_tab_data(tab_name)
        if current_entry and self.config_manager.get_app_config().skip_duplicate_ocr:
            def get_fp(e):
                s_str = "|".join(f"{s.stat}:{s.value}" for s in sorted(
                    e.substats, key=lambda x: x.stat))
                raw = f"{e.cost}|{e.main_stat}|{s_str}"
                return hashlib.md5(raw.encode("utf-8")).hexdigest()

            res_s_str = "|".join(f"{s.stat}:{s.value}" for s in sorted(
                result.substats, key=lambda x: x.stat))
            res_cost = result.cost if result.cost else current_entry.cost
            res_raw = f"{res_cost}|{result.main_stat}|{res_s_str}"
            result_fp = hashlib.md5(res_raw.encode("utf-8")).hexdigest()

            if result_fp == get_fp(current_entry):
                self.log_requested.emit(
                    f"[{tab_name}] OCR result skipped (Identical data)."
                )
                return

        # 2. Comparison with Equipped
        equipped = self.character_manager.get_equipped_echo(character, tab_name)
        if equipped:
            diffs = []
            eq_subs = {s.stat: s.value for s in equipped.substats}
            res_subs = {s.stat: s.value for s in result.substats}
            
            for s in (set(eq_subs.keys()) | set(res_subs.keys())):
                v1, v2 = eq_subs.get(s), res_subs.get(s)
                if v1 != v2:
                    if v1 is None: diffs.append(f"+{s}:{v2}")
                    elif v2 is None: diffs.append(f"-{s}:{v1}")
                    else: diffs.append(f"{s}:{v1}->{v2}")
            
            if diffs:
                self.log_requested.emit(
                    f"[{tab_name}] VS EQUIPPED: {', '.join(diffs)}"
                )
            else:
                self.log_requested.emit(f"[{tab_name}] Matches currently EQUIPPED.")

        # 3. Apply Data
        sub_vals = [(s.stat, s.value) for s in result.substats]
        content["widget"].set_data(result.main_stat, sub_vals)

        msg = f"[{tab_name}] OCR Result Applied."
        if result.main_stat:
            msg += f" Main: {self.tr(result.main_stat)}"
        self.log_requested.emit(msg)

    def save_tab_image(self, tab_name: str, original: Any, cropped: Any) -> None:
        """Store image data associated with a tab."""
        self._tab_images[tab_name] = TabImageData(original=original, cropped=cropped)

    def get_tab_image(self, tab_name: str) -> Optional[TabImageData]:
        """Retrieve stored image data for a tab."""
        return self._tab_images.get(tab_name)

    def save_tab_result(self, tab_name: str, html_content: str) -> None:
        """Store the calculation result HTML for a tab."""
        self._tab_results[tab_name] = TabResultData(content=html_content)

    def get_tab_result(self, tab_name: str) -> Optional[str]:
        """Retrieve stored result HTML for a tab."""
        data = self._tab_results.get(tab_name)
        return data.content if data else None

    def generate_scoreboard_image(
        self,
        character_name: str,
        output_path: str,
        generator: ScoreboardGenerator,
        score_calculator: ScoreCalculator,
        enabled_methods: Dict[str, bool],
        language: str = "ja",
    ) -> bool:
        """Gather all tab data and generate a build summary image."""
        try:
            entries = []
            images = {}
            scores = []

            config_key = self._validate_config_key()
            tab_names = self.data_manager.tab_configs.get(config_key, [])

            profile = self.character_manager.get_character_profile(character_name)
            weights = profile.weights if profile else {}
            element = profile.element if profile else "電導"
            config_bundle = score_calculator._get_config_bundle()

            for i, name in enumerate(tab_names):
                entry = self.extract_tab_data(name) or EchoEntry(tab_index=i, cost="?")
                entries.append(entry)

                img_data = self.get_tab_image(name)
                if img_data and img_data.cropped:
                    images[i] = img_data.cropped
                
                evaluation = score_calculator._process_echo_evaluation(
                    entry, weights, config_bundle, enabled_methods, 
                    character_name, "SCOREBOARD", name, record_history=False
                )
                scores.append(evaluation)

            return generator.generate(
                character_name=character_name,
                echo_entries=entries,
                echo_images=images,
                scores=scores,
                output_path=output_path,
                language=language,
                tr_func=self.tr,
                element=element
            )
        except Exception as e:
            self.logger.exception("Scoreboard generation failed")
            self.log_requested.emit(f"Scoreboard generation failed: {e}")
            return False

    def export_to_txt(self, parent_window: QWidget, text: str) -> None:
        """Prompt user to save text content to a file."""
        try:
            f_path, _ = QFileDialog.getSaveFileName(
                parent_window, "Save Result", "", 
                "Text Files (*.txt);;All Files (*.*)"
            )
            if f_path:
                with open(f_path, "w", encoding="utf-8") as f:
                    f.write(text)
                self.log_requested.emit(f"Exported result to: {f_path}")
        except Exception as e:
            self.logger.exception("Export failed")
            self.log_requested.emit(f"Export failed: {e}")