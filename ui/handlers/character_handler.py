from typing import Any
from ui.handlers.base import BaseHandler

class CharacterHandler(BaseHandler):
    """Handles character selection, profile updates, and auto-loading equipped echoes."""
    
    def on_character_change(self, index: int) -> None:
        if index < 0: return
        internal_name = self.ui.character_combo.itemData(index)
        if not internal_name:
            self.app.character_var = ""
            self.tab_mgr.apply_character_main_stats()
            self.app.events.save_config()
            return

        self.app.character_var = internal_name
        new_config = self.character_manager.get_character_config_key(internal_name)
        if new_config and new_config != self.app.current_config_key:
            if self.ui.config_combo:
                self.ui.config_combo.setCurrentText(new_config)
        else:
            self.tab_mgr.apply_character_main_stats(character=internal_name)

        self.app.ctx.theme_manager.apply_theme(self.app.app_config.theme)
        self.app.events.save_config()

        self._load_equipped_echoes(internal_name)
        
        # Check deferred OCR
        if hasattr(self.app.events, 'ocr_handler'):
            self.app.events.ocr_handler.check_deferred_ocr()

        if (getattr(self.app, "_waiting_for_character", False) or self.app.app_config.auto_calculate):
            score_mode = self.app.score_mode_var
            curr_idx = self.app.notebook.currentIndex()
            if self.tab_mgr.has_calculatable_data(mode=score_mode, current_index=curr_idx):
                self.app.trigger_calculation()

    def _load_equipped_echoes(self, internal_name: str) -> None:
        config_key = self.app.app_config.current_config_key
        tab_names = self.data_manager.tab_configs.get(config_key, [])
        all_equipped = self.character_manager.get_all_equipped_echoes(internal_name)
        used_keys = set()
        loaded_count = 0

        for name in tab_names:
            if self.tab_mgr.is_tab_empty(name) and name in all_equipped:
                equipped = all_equipped[name]
                if equipped:
                    self.tab_mgr.load_entry_into_tab(name, equipped)
                    used_keys.add(name)
                    loaded_count += 1

        for name in tab_names:
            if self.tab_mgr.is_tab_empty(name):
                target_cost = name.split('_')[0]
                for eq_key, eq_entry in all_equipped.items():
                    if eq_key in used_keys: continue
                    eq_cost = str(eq_entry.cost) if eq_entry.cost else eq_key.split('_')[0]
                    if eq_cost == target_cost:
                        self.tab_mgr.load_entry_into_tab(name, eq_entry)
                        used_keys.add(eq_key)
                        loaded_count += 1
                        break
        if loaded_count > 0:
            self.app.gui_log(f"Auto-load complete: {loaded_count} echoes restored.")

    def on_profiles_updated(self) -> None:
        all_chars = self.character_manager.get_all_characters(self.app.language)
        self.ui.update_character_combo(all_chars, self.app.character_var)
        self.ui.filter_characters_by_config()

    def on_character_registered(self, internal_char_name: str) -> None:
        self.app.gui_log(f"New character '{internal_char_name}' registered.")
        all_chars = self.character_manager.get_all_characters(self.app.language)
        self.ui.update_character_combo(all_chars, internal_char_name)
        self.app.character_var = internal_char_name
        new_config = self.character_manager.get_character_config_key(internal_char_name)
        if new_config:
            self.ui.config_combo.setCurrentText(new_config)
        self.ui.filter_characters_by_config()
        self.tab_mgr.apply_character_main_stats()
