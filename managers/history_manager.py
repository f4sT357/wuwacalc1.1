import json
import os
import logging
import re
from datetime import datetime
from typing import List, Dict, Any
from core.data_contracts import HistoryEntry
from utils.utils import get_app_path
from utils.constants import HISTORY_FILENAME


class HistoryManager:
    """Manages application history, including saving, loading, and filtering."""

    def __init__(self, filename: str = HISTORY_FILENAME, max_entries: int = 1000):
        self.history_path = os.path.join(get_app_path(), filename)
        self.max_entries = max_entries
        self.logger = logging.getLogger(__name__)
        self._history: List[HistoryEntry] = []
        self.load()

    def load(self) -> None:
        """Loads history from the JSON file."""
        if not os.path.exists(self.history_path):
            self._history = []
            return

        try:
            with open(self.history_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._history = [
                    HistoryEntry(
                        timestamp=item.get("timestamp", ""),
                        character=item.get("character", ""),
                        cost=item.get("cost", ""),
                        action=item.get("action", ""),
                        result=item.get("result", ""),
                        fingerprint=item.get("fingerprint", ""),
                        details=item.get("details", {}),
                    )
                    for item in data
                ]
            self.logger.info(f"Loaded {len(self._history)} history entries.")
        except Exception as e:
            self.logger.error(f"Failed to load history: {e}")
            self._history = []

    def save(self) -> bool:
        """Saves current history to the JSON file."""
        try:
            data = [
                {
                    "timestamp": h.timestamp,
                    "character": h.character,
                    "cost": h.cost,
                    "action": h.action,
                    "result": h.result,
                    "fingerprint": h.fingerprint,
                    "details": h.details,
                }
                for h in self._history
            ]
            with open(self.history_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            self.logger.error(f"Failed to save history: {e}")
            return False

    def add_entry(
        self,
        character: str,
        cost: str,
        action: str,
        result: str,
        fingerprint: str = "",
        details: Dict[str, Any] = None,
        duplicate_mode: str = "latest",
    ) -> None:
        """Adds a new history entry and prunes the list if necessary.

        duplicate_mode options:
        - "all": Keep all entries (no duplicate checking).
        - "latest": Remove existing entry with same fingerprint before adding new one.
        - "oldest": Skip adding if an entry with same fingerprint already exists.
        """
        if fingerprint and duplicate_mode != "all":
            exists = any(h.fingerprint == fingerprint for h in self._history)

            if exists:
                if duplicate_mode == "oldest":
                    self.logger.debug(
                        f"Skipping history entry due to 'oldest' mode and existing fingerprint: {fingerprint}"
                    )
                    return
                elif duplicate_mode == "latest":
                    # Remove existing entries with the same fingerprint
                    self._history = [h for h in self._history if h.fingerprint != fingerprint]

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = HistoryEntry(
            timestamp=timestamp,
            character=character,
            cost=cost,
            action=action,
            result=result,
            fingerprint=fingerprint,
            details=details or {},
        )

        # Insert at the beginning (newest first)
        self._history.insert(0, entry)

        # Prune if over limit
        if len(self._history) > self.max_entries:
            self._history = self._history[: self.max_entries]

        self.save()

    def find_duplicates(self, fingerprint: str) -> List[int]:
        """Returns a list of indices (IDs) where the fingerprint matches."""
        if not fingerprint:
            return []
        # Return indices of matching entries (0 is newest)
        return [i for i, h in enumerate(self._history) if h.fingerprint == fingerprint]

    def get_entries(
        self,
        keyword: str = "",
        character: str = "",
        cost: str = "",
        date_from: str = "",
        date_to: str = "",
        name_map: Dict[str, str] = None,
        rating: str = "",
    ) -> List[HistoryEntry]:
        """Returns filtered history entries."""
        filtered = self._history

        if keyword:
            kw = keyword.lower()
            new_filtered = []
            for h in filtered:
                match = kw in h.action.lower() or kw in h.result.lower() or kw in h.character.lower()

                if not match and name_map and h.character in name_map:
                    if kw in name_map[h.character].lower():
                        match = True

                if match:
                    new_filtered.append(h)
            filtered = new_filtered

        if character:
            filtered = [h for h in filtered if h.character == character]

        if cost:
            filtered = [h for h in filtered if h.cost == cost]

        if rating:
            # Match rating precisely. Use rating_key if available in details,
            # otherwise fallback to regex on the result string for backward compatibility.
            target_key = f"rating_{rating.lower()}_single"
            pattern = rf"(^|[\s\(]){re.escape(rating)}(\s|$|-)"

            new_filtered = []
            for h in filtered:
                # 1. Check details for rating_key (robust)
                r_key = h.details.get("rating_key")
                if r_key == target_key:
                    new_filtered.append(h)
                    continue

                # 2. Fallback to result string regex (backward compatibility)
                if re.search(pattern, h.result):
                    new_filtered.append(h)

            filtered = new_filtered

        if date_from:
            filtered = [h for h in filtered if h.timestamp >= date_from]

        if date_to:
            to_val = f"{date_to} 23:59:59"
            filtered = [h for h in filtered if h.timestamp <= to_val]

        return filtered

    def clear(self) -> None:
        """Clears all history."""
        self._history = []
        self.save()
