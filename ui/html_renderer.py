"""
Html Renderer Module

Responsible for generating visual HTML reports for echo evaluations, 
ensuring clean and readable presentation.
"""

from __future__ import annotations

from typing import Dict, Any, Optional, Tuple, TYPE_CHECKING

from core.data_contracts import EvaluationResult, EchoEntry
from utils.constants import STAT_CRIT_RATE, STAT_CRIT_DMG, STAT_ATK_PERCENT, STAT_ER

if TYPE_CHECKING:
    from core.echo_data import EchoData


class HtmlRenderer:
    """Generates styled HTML for displaying score results."""

    def __init__(self, tr_func, lang: str, text_color: str = "#333333"):
        """Initialize the renderer with basic style settings."""
        self.tr = tr_func
        self.language = lang
        self.text_color = text_color
        self.common_style = ""
        self._update_common_style()

    def set_text_color(self, color: str) -> None:
        """Update the base text color and refresh the stylesheet."""
        self.text_color = color
        self._update_common_style()

    def _update_common_style(self) -> None:
        """Update the internal CSS style based on current settings."""
        # Simple background for score blocks without shadows
        bg_color = "rgba(128, 128, 128, 0.1)"
        border_style = "1px solid rgba(128, 128, 128, 0.2)"

        self.common_style = f"""
        <!-- STYLE_START -->
        <style>
            body {{ 
                font-family: 'Segoe UI', 'Meiryo', sans-serif; 
                line-height: 1.4; 
                color: {self.text_color};
            }}
            h3 {{ color: {self.text_color}; margin-bottom: 5px; }}
            hr {{ border: 0; border-top: 1px solid rgba(128, 128, 128, 0.3); margin: 10px 0; }}
            .score-block {{
                margin-bottom: 12px; 
                padding: 10px;
                border-radius: 6px;
                background-color: {bg_color};
                border: {border_style};
            }}
            .progress-container {{
                width: 100%;
                background-color: rgba(128, 128, 128, 0.2);
                border-radius: 4px;
                height: 8px;
                margin: 4px 0 8px 0;
                overflow: hidden;
            }}
            .progress-bar {{
                height: 100%;
                border-radius: 4px;
            }}
        </style>
        <!-- STYLE_END -->
        """

    def refresh_html_style(self, html_content: str) -> str:
        """Update the style section of an existing HTML string."""
        import re
        if not html_content:
            return ""
        style_pattern = re.compile(r"<!-- STYLE_START -->.*?<!-- STYLE_END -->", re.DOTALL)
        if "<!-- STYLE_START -->" in html_content:
            return style_pattern.sub(self.common_style.strip(), html_content)
        return html_content

    def _get_progress_bar(self, percentage: float, color: str = None) -> str:
        """Generate HTML for a visual progress bar."""
        if color is None:
            if percentage >= 85: color = "#FF4500"
            elif percentage >= 70: color = "#E67E22"
            elif percentage >= 50: color = "#2980B9"
            elif percentage >= 30: color = "#27AE60"
            else: color = "#7F8C8D"
        
        display_pct = min(100.0, max(0.0, percentage))
        return f"""
        <div class="progress-container">
            <div class="progress-bar" style="width: {display_pct}%; background-color: {color};"></div>
        </div>
        """

    def _get_rating_color(self, rating_text: str) -> str:
        """Map rating levels to distinct colors."""
        if any(kw in rating_text for kw in ["SSS", "Perfect", "God"]): return "#FF4500"
        if any(kw in rating_text for kw in ["SS", "Top", "Excellent"]): return "#E67E22"
        if any(kw in rating_text for kw in ["S", "Win"]): return "#2980B9"
        if any(kw in rating_text for kw in ["A", "Good"]): return "#27AE60"
        return "#7F8C8D"

    def format_score_block(self, label: str, score: float, rating_info: Any, desc: str) -> str:
        """Format a single scoring methodology result block."""
        if isinstance(rating_info, tuple):
            rating_text = self.tr(rating_info[0], *rating_info[1:])
        else:
            rating_text = self.tr(rating_info)

        color = self._get_rating_color(rating_text)
        return f"""
        <div class='score-block'>
            <b>[{label}]</b><br>
            <b>Score: {score:.2f}</b><br>
            <span style='color:{color}; font-weight: bold;'>Rating: {rating_text}</span><br>
            <small><i>{desc}</i></small>
        </div>
        """

    def render_single_score(
        self,
        character: str,
        tab_name: str,
        entry: EchoEntry,
        main_stat: str,
        echo: EchoData,
        evaluation: EvaluationResult,
    ) -> str:
        """Generate comprehensive HTML report for a single Echo."""
        title = self.tr("individual_score_title", character, tab_name).replace("\n", "")
        html = self.common_style
        html += f"<h3><u>{title}</u></h3>"
        html += f"<hr>"
        
        # New: Display consistency advice
        if evaluation.consistency_advice:
            html += f"<div style='color: #ff5555; background: rgba(255,0,0,0.1); padding: 5px; border-left: 3px solid #ff5555; margin-bottom: 10px;'>"
            html += f"⚠️ {evaluation.consistency_advice}</div>"

        # New: Display build optimization advice
        if evaluation.advice_list:
            html += "<div style='margin-bottom: 10px; font-size: 0.95em; color: #88ccff; background: rgba(0,0,0,0.2); padding: 5px; border-radius: 4px;'>"
            for advice in evaluation.advice_list:
                html += f"• {advice}<br>"
            html += "</div>"
        
        html += f"<b>{self.tr('echo_info').replace('\n', '')}</b><br>"
        html += f"&nbsp;&nbsp;• {self.tr('cost')}: {entry.cost}<br>"
        html += f"&nbsp;&nbsp;• {self.tr('main_stat')}: {self.tr(main_stat)}<br>"
        html += f"&nbsp;&nbsp;• {self.tr('level', echo.level)}<br>"
        html += f"&nbsp;&nbsp;• {self.tr('effective_substat_count', evaluation.effective_count)}<br>"

        html += f"<br><b>{self.tr('substats')}</b><br>"
        if echo.substats:
            for name, val in echo.substats.items():
                html += f"&nbsp;&nbsp;&nbsp;&nbsp;{self.tr(name)}: {val}<br>"
        else:
            html += f"&nbsp;&nbsp;{self.tr('none')}<br>"
        html += "<hr>"

        # Methods breakdown
        method_map = {
            "achievement": (self.tr("achievement_rate_label"), self.tr("achievement_rate_desc")),
            "normalized": (self.tr("method_normalized"), self.tr("normalized_score_desc")),
            "ratio": (self.tr("method_ratio"), self.tr("ratio_score_desc")),
            "roll": (self.tr("method_roll"), self.tr("roll_quality_desc")),
            "effective": (self.tr("method_effective"), self.tr("effective_stat_desc")),
            "cv": (self.tr("method_cv"), self.tr("cv_score_desc")),
        }

        eval_scores = evaluation.individual_scores
        for m_id in ["achievement", "normalized", "ratio", "roll", "effective", "cv"]:
            if m_id in eval_scores and m_id in method_map:
                score = eval_scores[m_id]
                label, desc = method_map[m_id]
                rating = evaluation.rating if m_id == "achievement" else m_id
                html += self.format_score_block(label, score, rating, desc)

        html += f"<hr>"
        
        if evaluation.estimated_stats:
            html += f"<b>{self.tr('estimated_total_stats').replace('\n', '')}</b><br>"
            priority = [STAT_CRIT_RATE, STAT_CRIT_DMG, STAT_ATK_PERCENT, STAT_ER]
            
            for sname in priority:
                if sname in evaluation.estimated_stats:
                    val = evaluation.estimated_stats[sname]
                    html += f"&nbsp;&nbsp;• {self.tr(sname)}: {val:.1f}<br>"
            
            for sname, val in sorted(evaluation.estimated_stats.items()):
                if sname not in priority and val > 0 and not sname.startswith(("Total ", "Goal ")):
                    html += f"&nbsp;&nbsp;• {self.tr(sname)}: {val:.1f}<br>"
            
            for sname, val in evaluation.estimated_stats.items():
                if sname.startswith("Total "):
                    html += f"<br><b>&nbsp;&nbsp;{sname}: {val:.1f}</b><br>"
                if sname.startswith("Goal "):
                    html += f"<b>&nbsp;&nbsp;{sname}: {val:.1f}%</b><br>"
            
            html += f"<hr>"

        html += "<hr>"

        # Overall summary
        html += f"<b>{self.tr('overall_eval')}</b><br>"
        html += f"<b>{self.tr('achievement_rate_label')}: {evaluation.total_score:.2f}%</b><br>"
        html += self._get_progress_bar(evaluation.total_score)

        final_rating = self.tr(evaluation.rating)
        final_color = self._get_rating_color(final_rating)
        html += f"<span style='color:{final_color}; font-size: 1.2em;'><b>{self.tr('overall_rating')}: {final_rating}</b></span><br>"

        if evaluation.estimated_stats:
            for sname, val in evaluation.estimated_stats.items():
                if sname.startswith("Goal "):
                    html += self._get_progress_bar(val, "#FFD700")

        if evaluation.comparison_diff is not None:
            diff = evaluation.comparison_diff
            d_color = "#32CD32" if diff >= 0 else "#FF4500"
            html += f"<b style='color:{d_color};'>{self.tr('vs_equipped')}: {'+' if diff >= 0 else ''}{diff:.2f}%</b><br>"

        html += f"{self.tr('recommendation')}: {self.tr(evaluation.recommendation)}<br>"
        return html

    def render_batch_score(
        self,
        character: str,
        calculated_count: int,
        total_count: int,
        all_evaluations: list,
        total_scores: dict,
        enabled_methods: dict,
    ) -> str:
        """Generate summary HTML report for multiple Echos."""
        batch_title = self.tr("batch_score_title", character).replace("\n", "")
        html = self.common_style
        html += f"<h3><u>{batch_title}</u></h3>"
        html += f"<b>{self.tr('calculated', calculated_count, total_count)}</b><br><hr>"

        for eval_data in all_evaluations:
            html += f"<b>--- {eval_data['tab_name']} ---</b><br>"
            score = eval_data["total"]
            color = "#FF4500" if score >= 85 else "#E67E22" if score >= 70 else "#2980B9" if score >= 50 else "#27AE60"
            html += f"<b>{self.tr('total_score')}: <span style='color:{color}'>{score:.2f}%</span></b><br>"
            html += self._get_progress_bar(score, color)
            html += f"<small>{self.tr('recommendation')}: {eval_data['recommendation']}</small><br><br>"

        html += "<hr><b>Summary Averages</b><br>"
        avg_total = total_scores["total"] / calculated_count
        html += f"<b>Average Achievement: {avg_total:.2f}%</b><br>"
        html += self._get_progress_bar(avg_total)
        return html