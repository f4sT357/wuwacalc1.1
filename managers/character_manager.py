import json
import logging
import os
import copy
import re
from PySide6.QtCore import QObject, Signal
from typing import Optional

from utils.utils import get_app_path, get_resource_path
from utils.constants import DEFAULT_COST_CONFIG, DIR_CHARACTER_SETTINGS, EQUIPPED_ECHOES_FILENAME, STAT_CRIT_RATE
from core.data_contracts import CharacterProfile


def _sanitize_filename(name: str) -> str:
    """Sanitizes a string to be a valid filename."""
    return re.sub(r"[^0-9A-Za-z一-龠ぁ-んァ-ヴー_-]", "_", name)


class CharacterManager(QObject):
    """Manages character data, including loading, saving, and registration."""

    profiles_updated = Signal()
    character_registered = Signal(str)  # Emits the internal name of the new character

    def __init__(self, logger: logging.Logger, data_manager, parent=None):
        super().__init__(parent)
        self.logger = logger
        self.data_manager = data_manager

        # Deep copy data from DataManager to avoid modifying source
        self._stat_weights = copy.deepcopy(data_manager.character_stat_weights)
        self._main_stats = copy.deepcopy(data_manager.character_main_stats)
        self._name_map_jp_to_en = copy.deepcopy(data_manager.char_name_map_jp_to_en)
        self._name_map_en_to_jp = {v: k for k, v in self._name_map_jp_to_en.items()}
        self._stat_offsets = {}  # Stores dictionary of offsets for each character
        self._base_stats = {}  # Stores base stats (Char + Weapon)
        self._ideal_stats = {}  # Stores target/ideal stats
        self._scaling_stats = {}  # Stores primary scaling stat name
        self._elements = {}  # New: Stores character element
        self._equipped_echoes = {}  # character -> {slot -> EchoEntry}

        self.tab_configs = data_manager.tab_configs

        # Initialize with deep copy from data manager
        self._character_config_map = copy.deepcopy(data_manager.character_config_map)

        self._load_character_profiles()
        self._load_equipped_echoes()

    def _load_equipped_echoes(self):
        """Loads equipped echoes from a JSON file."""
        file_path = os.path.join(get_app_path(), EQUIPPED_ECHOES_FILENAME)
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Convert dicts back to EchoEntry objects (simplified for now)
                    from core.data_contracts import EchoEntry, SubStat

                    for char, slots in data.items():
                        self._equipped_echoes[char] = {}
                        for slot, entry_dict in slots.items():
                            substats = [SubStat(**s) for s in entry_dict.get("substats", [])]
                            self._equipped_echoes[char][slot] = EchoEntry(
                                tab_index=0,
                                cost=entry_dict.get("cost"),
                                main_stat=entry_dict.get("main_stat"),
                                substats=substats,
                            )
            except Exception as e:
                self.logger.error(f"Failed to load equipped echoes: {e}")

    def save_equipped_echo(self, character: str, slot: str, entry: any):
        """Saves an echo entry as equipped for a character's slot."""
        if not character or not slot or not entry:
            return

        if character not in self._equipped_echoes:
            self._equipped_echoes[character] = {}

        self._equipped_echoes[character][slot] = entry

        # Persist to file
        file_path = os.path.join(get_app_path(), EQUIPPED_ECHOES_FILENAME)
        try:
            # Convert to serializable format
            output = {}
            for char, slots in self._equipped_echoes.items():
                output[char] = {}
                for s_key, e_val in slots.items():
                    output[char][s_key] = {
                        "cost": e_val.cost,
                        "main_stat": e_val.main_stat,
                        "substats": [{"stat": s.stat, "value": s.value} for s in e_val.substats],
                    }
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(output, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save equipped echoes: {e}")

    def get_equipped_echo(self, character: str, slot: str) -> Optional[any]:
        """Gets the equipped echo entry for a character's slot."""
        return self._equipped_echoes.get(character, {}).get(slot)

    def get_all_equipped_echoes(self, character: str) -> dict:
        """Gets all equipped echo entries for a character as {slot: entry}."""
        return self._equipped_echoes.get(character, {})

    def _load_character_profiles(self):
        """Loads character profiles from JSON files in the character_settings_jsons directory."""
        self.logger.info("Loading character profiles...")

        # Paths to check: bundled resources first, then user directory (user dir can override)
        search_dirs = [get_resource_path(DIR_CHARACTER_SETTINGS), os.path.join(get_app_path(), DIR_CHARACTER_SETTINGS)]

        # Use a set to avoid loading the same file twice if paths happen to be the same
        loaded_files = set()

        for char_dir in search_dirs:
            if not os.path.isdir(char_dir):
                continue

            for filename in os.listdir(char_dir):
                if filename.endswith(".json"):
                    filepath = os.path.join(char_dir, filename)
                    # Simple duplicate check by filename (overriding bundled with user file if names match)
                    if filename in loaded_files:
                        continue

                    try:
                        with open(filepath, "r", encoding="utf-8") as f:
                            data = json.load(f)

                        internal_name = data.get("character")
                        jp_name = data.get("character_jp")

                        if not internal_name:
                            # Attempt to derive from filename for legacy files
                            internal_name = filename.replace("_character.json", "")
                            self.logger.warning(
                                f"Legacy character file '{filename}' detected. Using filename as internal name: {internal_name}"
                            )

                        if not internal_name:
                            self.logger.warning(f"Skipping profile from '{filename}': missing 'character' field.")
                            continue

                        weights = data.get("character_weights")
                        mainstats = data.get("character_mainstats")
                        costkey = data.get("costkey")
                        config = data.get("config")

                        # Load offsets and new stat fields
                        stat_offsets = data.get("stat_offsets", {})
                        if not stat_offsets and "crit_offset" in data:
                            stat_offsets[STAT_CRIT_RATE] = data["crit_offset"]

                        base_stats = data.get("base_stats", {})
                        ideal_stats = data.get("ideal_stats", {})
                        scaling_stat = data.get("scaling_stat", "攻撃力")
                        element = data.get("element", "電導")

                        if not all([weights, mainstats, (costkey or config)]):
                            self.logger.warning(f"Skipping incomplete character profile: {filename}")
                            continue

                        if not jp_name:
                            jp_name = self.get_display_name(internal_name)

                        # Update data stores
                        internal_name = data.get("character") or filename.replace("_character.json", "")
                        weights = data.get("character_weights")
                        mainstats = self._normalize_main_stats_keys(data.get("character_mainstats", {}))

                        self._stat_weights[internal_name] = weights
                        self._main_stats[internal_name] = mainstats
                        self._name_map_en_to_jp[internal_name] = jp_name
                        self._name_map_jp_to_en[jp_name] = internal_name
                        self._character_config_map[internal_name] = config or self._normalize_cost_key(
                            costkey, DEFAULT_COST_CONFIG
                        )
                        self._stat_offsets[internal_name] = stat_offsets
                        self._base_stats[internal_name] = base_stats
                        self._ideal_stats[internal_name] = ideal_stats
                        self._scaling_stats[internal_name] = scaling_stat
                        self._elements[internal_name] = element

                        self.logger.info(f"Loaded character profile: {internal_name}")
                        loaded_files.add(filename)

                    except json.JSONDecodeError:
                        self.logger.error(f"Failed to decode JSON from {filename}")
                    except Exception as e:
                        self.logger.error(f"Failed to load character profile {filename}: {e}", exc_info=True)

        self.logger.info("Finished loading character profiles.")
        self.profiles_updated.emit()

    def _normalize_main_stats_keys(self, mainstats: dict) -> dict:
        """Converts long keys like 'cost3_echo_1' to short keys like '3_1'."""
        normalized = {}
        for k, v in mainstats.items():
            if isinstance(k, str) and "cost" in k:
                new_key = k.replace("cost", "").replace("echo_", "")
                if new_key.endswith("_"):
                    new_key = new_key[:-1]
                normalized[new_key] = v
            else:
                normalized[str(k)] = v
        return normalized

    def register_character(
        self,
        name_jp: str,
        name_en: str,
        costkey: str,
        mainstats: dict,
        weights: dict,
        stat_offsets: dict = None,
        base_stats: dict = None,
        ideal_stats: dict = None,
        scaling_stat: str = "攻撃力",
        element: str = "電導",
    ) -> None:
        """Registers a new character and saves its profile to a JSON file."""
        internal_char_name = name_en
        if stat_offsets is None:
            stat_offsets = {}
        if base_stats is None:
            base_stats = {}
        if ideal_stats is None:
            ideal_stats = {}

        # Normalize mainstats keys before saving
        normalized_mainstats = self._normalize_main_stats_keys(mainstats)

        try:
            # --- Save to JSON file ---
            base_dir = get_app_path()
            target_dir = os.path.join(base_dir, DIR_CHARACTER_SETTINGS)
            os.makedirs(target_dir, exist_ok=True)

            # Use English name for filename for consistency
            safe_name = _sanitize_filename(internal_char_name)
            file_path = os.path.join(target_dir, f"{safe_name}_character.json")

            normalized_key = self._normalize_cost_key(costkey, DEFAULT_COST_CONFIG)

            payload = {
                "character": internal_char_name,
                "character_jp": name_jp,
                "costkey": costkey,
                "config": normalized_key,
                "character_mainstats": normalized_mainstats,
                "character_weights": weights,
                "stat_offsets": stat_offsets,
                "base_stats": base_stats,
                "ideal_stats": ideal_stats,
                "scaling_stat": scaling_stat,
                "element": element,
            }
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)

            self.logger.info(f"Character profile saved: {internal_char_name} -> {file_path}")

            # --- Update internal data stores ---
            self._stat_weights[internal_char_name] = weights
            self._main_stats[internal_char_name] = normalized_mainstats
            self._name_map_en_to_jp[internal_char_name] = name_jp
            self._name_map_jp_to_en[name_jp] = internal_char_name
            self._character_config_map[internal_char_name] = normalized_key
            self._stat_offsets[internal_char_name] = stat_offsets
            self._base_stats[internal_char_name] = base_stats
            self._ideal_stats[internal_char_name] = ideal_stats
            self._scaling_stats[internal_char_name] = scaling_stat
            self._elements[internal_char_name] = element

            # --- Emit signal ---
            self.character_registered.emit(internal_char_name)
            return True

        except Exception as e:
            self.logger.error(
                f"Error registering or saving character profile for '{internal_char_name}': {e}", exc_info=True
            )
            return False
            # Optionally, re-raise or emit an error signal

    def get_all_characters(self, lang: str = "ja") -> list[tuple[str, str]]:
        """Returns a list of (display_name, internal_name) for all characters."""
        # Sorting by display name
        return sorted(
            [(self.get_display_name(name, lang), name) for name in self._stat_weights.keys()], key=lambda x: x[0]
        )

    def get_display_name(self, internal_name: str, lang: str = "ja") -> str:
        """Gets the display name for a given internal English name."""
        if lang == "en":
            return internal_name
        return self._name_map_en_to_jp.get(internal_name, internal_name)

    def get_internal_name(self, display_name: str) -> str:
        """Gets the internal English name for a given Japanese display name."""
        # Fallback for when the internal name is passed directly
        if display_name in self._name_map_en_to_jp:
            return display_name
        return self._name_map_jp_to_en.get(display_name, display_name)

    def get_stat_weights(self, internal_name: str) -> dict:
        """Gets the stat weights for a character."""
        return self._stat_weights.get(internal_name, self._stat_weights.get("General", {}))

    def get_main_stats(self, internal_name: str) -> dict:
        """Gets the main stats for a character."""
        return self._main_stats.get(internal_name, {})

    def get_character_config_key(self, internal_name: str) -> str:
        """Gets the cost config key for a character."""
        return self._character_config_map.get(internal_name, "")

    def get_character_config_map(self) -> dict:
        """Returns the entire character to config key map."""
        return self._character_config_map

    def get_character_list_by_config(self, config_key: str) -> list[dict]:
        """
        Returns a list of characters that match the given cost configuration.
        Each item is a dict with 'name_jp' and 'name_en'.
        """
        results = []
        for internal_name, config in self._character_config_map.items():
            if config == config_key:
                results.append({"name_en": internal_name, "name_jp": self.get_display_name(internal_name)})
        return results

    def add_or_update_character_temp(self, internal_name: str, jp_name: str, weights: dict, mainstats: dict):
        """
        Adds or updates a character's data in memory for the current session without saving to a file.
        This is used for loading character data from build/session files.
        """
        if not all([internal_name, jp_name, weights, mainstats]):
            self.logger.warning(f"Attempted to temporarily add character with incomplete data: EN='{internal_name}'")
            return

        self.logger.info(f"Temporarily updating data for character: {internal_name}")
        self._stat_weights[internal_name] = weights
        self._main_stats[internal_name] = mainstats
        self._name_map_en_to_jp[internal_name] = jp_name
        self._name_map_jp_to_en[jp_name] = internal_name

        # This might cause the character combobox to update, which is desired.
        self.profiles_updated.emit()

    def _normalize_cost_key(self, costkey: any, current_config: str) -> str:
        """Normalizes a cost key to a valid tab configuration."""
        if isinstance(costkey, str):
            digits = "".join(ch for ch in costkey if ch.isdigit())
            if digits in self.tab_configs:
                return digits
        elif isinstance(costkey, (list, tuple)):
            digits = "".join(str(int(c)) for c in costkey)
            if digits in self.tab_configs:
                return digits

        if current_config in self.tab_configs:
            return current_config
        return DEFAULT_COST_CONFIG  # Fallback

    def get_character_profile(self, internal_name: str) -> Optional[CharacterProfile]:
        """
        Retrieves the full profile for a character.

        Args:
            internal_name: The internal English ID of the character.

        Returns:
            CharacterProfile object or None if not found.
        """
        if not internal_name:
            return None

        jp_name = self.get_display_name(internal_name)
        cost_config = self.get_character_config_key(internal_name) or DEFAULT_COST_CONFIG

        # Get main stats
        main_stats = self.get_main_stats(internal_name) or {}

        # Get weights
        weights = self.get_stat_weights(internal_name) or {}

        # Get stat offsets
        stat_offsets = self._stat_offsets.get(internal_name, {})
        base_stats = self._base_stats.get(internal_name, {})
        ideal_stats = self._ideal_stats.get(internal_name, {})
        scaling_stat = self._scaling_stats.get(internal_name, "攻撃力")
        element = self._elements.get(internal_name, "電導")

        return CharacterProfile(
            internal_name=internal_name,
            jp_name=jp_name,
            cost_config=cost_config,
            main_stats=main_stats,
            weights=weights,
            stat_offsets=stat_offsets,
            base_stats=base_stats,
            ideal_stats=ideal_stats,
            scaling_stat=scaling_stat,
            element=element,
        )
