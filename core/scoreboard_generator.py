import os
import logging
from typing import List, Dict, Optional, Any
from PIL import Image, ImageDraw, ImageFont

from core.data_contracts import EchoEntry, EvaluationResult

# Constants for layout
WIDTH = 1920
HEIGHT = 1080
CARD_BG_COLOR = (50, 50, 50)
TEXT_COLOR = (255, 255, 255)

SCORE_COLOR_S = (255, 100, 100)
SCORE_COLOR_A = (255, 165, 0)
SCORE_COLOR_B = (100, 200, 100)
SCORE_COLOR_C = (150, 150, 150)

class ScoreboardGenerator:
    # Theme colors for elements
    ELEMENT_THEMES = {
        "焦熱": {"bg": (40, 20, 20), "accent": (255, 69, 0)},
        "凝縮": {"bg": (20, 30, 45), "accent": (0, 191, 255)},
        "気動": {"bg": (20, 40, 30), "accent": (50, 205, 50)},
        "電導": {"bg": (35, 25, 45), "accent": (186, 85, 211)},
        "消滅": {"bg": (25, 20, 35), "accent": (138, 43, 226)},
        "回折": {"bg": (45, 40, 25), "accent": (255, 215, 0)},
    }
    DEFAULT_THEME = {"bg": (30, 30, 30), "accent": (255, 215, 0)}

    def __init__(self, logger: logging.Logger = None):
        self.logger = logger or logging.getLogger(__name__)
        self.font_path = self._find_font()
        self._font_cache = {}

    def _find_font(self) -> str:
        """Attempts to find a suitable Japanese font."""
        candidates = [
            "C:\\Windows\\Fonts\\meiryo.ttc",
            "C:\\Windows\\Fonts\\yugothr.ttc",
            "C:\\Windows\\Fonts\\yugothic.ttf",
            "C:\\Windows\\Fonts\\msgothic.ttc",
            "arial.ttf",
        ]
        for path in candidates:
            if os.path.exists(path):
                return path
        return "arial.ttf"

    def _get_font(self, size: int) -> ImageFont.FreeTypeFont:
        """Loads and caches fonts of various sizes."""
        if size in self._font_cache:
            return self._font_cache[size]
        try:
            if self.font_path and os.path.exists(self.font_path):
                font = ImageFont.truetype(self.font_path, size)
                self._font_cache[size] = font
                return font
        except Exception:
            pass
        return ImageFont.load_default()

    def _get_element_colors(self, element: str) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
        """Returns (BG_COLOR, ACCENT_COLOR) for a given element."""
        theme = self.ELEMENT_THEMES.get(element, self.DEFAULT_THEME)
        return theme["bg"], theme["accent"]

    def generate(
        self,
        character_name: str,
        echo_entries: List[EchoEntry],
        echo_images: Dict[int, Image.Image],
        scores: List[EvaluationResult],
        output_path: str,
        language: str = "en",
        tr_func: Any = None,
        element: str = "電導",
    ) -> bool:
        """Generates a scoreboard image and saves it to output_path."""
        try:
            def tr(key, default=None):
                if tr_func:
                    res = tr_func(key)
                    return res if res != key else (default if default else key)
                return default if default else key

            bg_color, accent_color = self._get_element_colors(element)
            img = Image.new("RGB", (WIDTH, HEIGHT), bg_color)
            draw = ImageDraw.Draw(img)

            title_font = self._get_font(80)
            header_text = f"{tr('echo_build_title', 'Echo Build')}: {character_name}"
            draw.text((50, 50), header_text, font=title_font, fill=TEXT_COLOR)

            avg_score = 0
            if scores:
                valid_scores = [s.total_score for s in scores if s is not None]
                if valid_scores:
                    avg_score = sum(valid_scores) / len(valid_scores)

            avg_text = f"{tr('average_score_label', 'Average Score')}: {avg_score:.1f}"
            draw.text((50, 150), avg_text, font=info_font, fill=accent_color)

            # Grid layout settings: 5 columns in 1 row
            card_w, card_h = 360, 720
            margin_x = 20
            row_y = 250
            total_grid_w = (card_w * 5) + (margin_x * 4)
            x_start = (WIDTH - total_grid_w) // 2

            for i, entry in enumerate(echo_entries):
                if i >= 5: break
                x = x_start + i * (card_w + margin_x)
                y = row_y
                self._draw_card(img, x, y, card_w, card_h, entry, scores[i] if i < len(scores) else None, i, echo_images, tr, accent_color)

            img.save(output_path)
            return True
        except Exception as e:
            self.logger.exception(f"Scoreboard Error: {e}")
            return False

    def _draw_card(self, canvas, x, y, w, h, entry, score, index, image_map, tr, accent_color):
        draw = ImageDraw.Draw(canvas)
        draw.rectangle([x, y, x + w, y + h], fill=CARD_BG_COLOR, outline=(100, 100, 100), width=2)
        px, py = 20, 20
        cx, cy = x + px, y + py
        cw = w - px * 2

        header_font = self._get_font(32)
        draw.text((cx, cy), f"{tr('cost_label_short', 'Cost')} {entry.cost or '?'}", font=header_font, fill=accent_color)

        if score:
            color = {"sss": SCORE_COLOR_S, "ss": SCORE_COLOR_S, "s_": SCORE_COLOR_A, "a_": SCORE_COLOR_A, "b_": SCORE_COLOR_B}.get(score.rating[:2], SCORE_COLOR_C)
            score_text = f"{score.total_score:.1f} ({self._format_rating(score.rating)})"
            bbox = draw.textbbox((0, 0), score_text, font=header_font)
            draw.text((x + w - px - (bbox[2] - bbox[0]), cy), score_text, font=header_font, fill=color)

        cy += 50
        if index in image_map and image_map[index]:
            thumb = image_map[index].copy()
            thumb.thumbnail((cw, 180)) # Slightly taller thumbnail area
            canvas.paste(thumb, (x + (w - thumb.width) // 2, cy))
            cy += thumb.height + 20
        else: cy += 20

        main_font = self._get_font(28)
        if entry.main_stat:
            draw.text((cx, cy), f"{tr('main_stat', 'Main')}: {tr(entry.main_stat, entry.main_stat)}", font=main_font, fill=TEXT_COLOR)
        cy += 40
        draw.line([cx, cy, x + w - px, cy], fill=(150, 150, 150), width=1)
        cy += 15

        sub_font = self._get_font(24)
        for sub in entry.substats:
            draw.text((cx, cy), tr(sub.stat, sub.stat), font=sub_font, fill=(200, 200, 200))
            val_str = sub.value
            bbox = draw.textbbox((0, 0), val_str, font=sub_font)
            draw.text((x + w - px - (bbox[2] - bbox[0]), cy), val_str, font=sub_font, fill=TEXT_COLOR)
            cy += 32

        if score:
            draw.text((cx, y + h - 50), f"{tr('effective_count_label', 'Effective Stats')}: {score.effective_count}", font=self._get_font(22), fill=(180, 180, 180))

    def _format_rating(self, rating_key: str) -> str:
        for r in ["SSS", "SS", "S", "A", "B", "C"]:
            if r.lower() in rating_key: return r
        return "?"