from typing import Any, Dict
from datetime import datetime
from ui.handlers.base import BaseHandler
from PySide6.QtWidgets import QMessageBox, QFileDialog
from core.data_contracts import EchoEntry

class CalculationHandler(BaseHandler):
    """Handles triggers for score calculation and report generation."""
    
    def trigger_calculation(self) -> None:
        try:
            if not self.app.character_var:
                self.app._waiting_for_character = True
                self.ui.result_text.setHtml(
                    f"<h3 style='color: orange;'>{self.app.tr('waiting_for_character')}</h3>"
                )
                return

            self.app._waiting_for_character = False
            self.app.show_duplicate_entries()

            enabled_methods = self.app.app_config.enabled_calc_methods
            if self.app.score_mode_var == "single":
                tab_name = self.app.get_selected_tab_name()
                entry = self.tab_mgr.extract_tab_data(tab_name)
                if entry:
                    self.score_calc.calculate_single(
                        self.app.character_var, tab_name, entry, enabled_methods
                    )
            else:
                tabs_data = {}
                for n in self.tab_mgr.tabs_content.keys():
                    if self.tab_mgr.has_substats(n):
                        tabs_data[n] = self.tab_mgr.extract_tab_data(n)
                
                if not tabs_data:
                    self.app.gui_log("No calculatable data found in any tab.")
                    return

                self.score_calc.calculate_batch(
                    self.app.character_var, tabs_data, enabled_methods, self.app.language
                )
        except Exception as e:
            self.logger.exception(f"Calculation trigger error: {e}")

    def generate_scoreboard(self) -> None:
        from core.scoreboard_generator import ScoreboardGenerator

        if not self.app.character_var:
            QMessageBox.warning(self.app, self.app.tr("warning"), self.app.tr("waiting_for_character"))
            return

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"{self.app.character_var}_Build_{ts}.png"
        file_path, _ = QFileDialog.getSaveFileName(
            self.app, self.app.tr("save_scoreboard"), default_name, "Images (*.png)"
        )
        if not file_path:
            return

        try:
            generator = ScoreboardGenerator(logger=self.logger)
            success = self.tab_mgr.generate_scoreboard_image(
                character_name=self.app.character_var,
                output_path=file_path,
                generator=generator,
                score_calculator=self.score_calc,
                enabled_methods=self.app.app_config.enabled_calc_methods,
                language=self.app.language
            )
            if success:
                QMessageBox.information(self.app, self.app.tr("info"), self.app.tr("save_success"))
        except Exception as e:
            self.logger.exception(f"Scoreboard generation error: {e}")
