"""
OCR Parsing Module

Responsible for extracting structured data from raw OCR text.
"""

import re
import logging
from typing import List, Tuple, Optional, Any, Dict
from core.data_contracts import SubStat, OCRResult


class OcrParser:
    def __init__(self, data_manager: Any, tr_func: Any):
        self.data_manager = data_manager
        self.tr = tr_func
        self.logger = logging.getLogger(__name__)

    def parse(self, raw_text: str, language: str) -> OCRResult:
        """
        Parses raw OCR text into a structured OCRResult.
        """
        if not raw_text:
            return OCRResult(substats=[], log_messages=[], cost=None, main_stat=None, raw_text="")

        substats, log_messages = self.parse_substats(raw_text, language)
        cost = self.detect_cost(raw_text)
        main_stat = self.detect_main_stat(raw_text, cost)

        if main_stat:
            log_messages.append(f"OCR auto-fill: Main Stat -> {self.tr(main_stat)}")

        return OCRResult(
            substats=substats, log_messages=log_messages, cost=cost, main_stat=main_stat, raw_text=raw_text
        )

    def parse_with_boxes(self, raw_text: str, data: Dict[str, Any], language: str) -> OCRResult:
        """
        Parses raw text and Tesseract data into a structured OCRResult with bounding boxes.
        """
        result = self.parse(raw_text, language)
        
        # Link boxes to the parsed results
        processed_boxes = self._extract_boxes_from_tess_data(data)
        
        # Main stat box
        if result.main_stat:
            result.boxes["main_stat"] = self._find_box_for_text(result.main_stat, processed_boxes)
            
        # Cost box
        if result.cost:
            result.boxes["cost"] = self._find_box_for_text(result.cost, processed_boxes)

        # Substat boxes
        for sub in result.substats:
            # Try to find a box that contains BOTH the stat name and potentially the value
            # This is heuristic but usually works well for line-by-line OCR
            sub.box = self._find_box_for_stat_line(sub.stat, sub.value, processed_boxes)
            
        return result

    def _extract_boxes_from_tess_data(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        boxes = []
        n_boxes = len(data['text'])
        for i in range(n_boxes):
            if data['text'][i].strip():
                boxes.append({
                    'text': data['text'][i],
                    'left': data['left'][i],
                    'top': data['top'][i],
                    'width': data['width'][i],
                    'height': data['height'][i]
                })
        return boxes

    def _find_box_for_text(self, text: str, boxes: List[Dict[str, Any]]) -> Optional[Tuple[int, int, int, int]]:
        # Find a box that contains the text
        for box in boxes:
            if text in box['text']:
                return (box['left'], box['top'], box['width'], box['height'])
        return None

    def _find_box_for_stat_line(self, stat: str, val: str, boxes: List[Dict[str, Any]]) -> Optional[Tuple[int, int, int, int]]:
        # Heuristic: find boxes on the same horizontal line that contain the stat name and value
        target_boxes = []
        for box in boxes:
            if stat in box['text'] or val in box['text']:
                target_boxes.append(box)
        
        if not target_boxes:
            return None
            
        # Group boxes that are vertically close (same line)
        left = min(b['left'] for b in target_boxes)
        top = min(b['top'] for b in target_boxes)
        right = max(b['left'] + b['width'] for b in target_boxes)
        bottom = max(b['top'] + b['height'] for b in target_boxes)
        
        return (left, top, right - left, bottom - top)

    def detect_main_stat(self, ocr_text: str, cost: Optional[str]) -> Optional[str]:
        """Detects the main stat from the OCR text."""
        if not ocr_text:
            return None

        possible_stats = []
        if cost and cost in self.data_manager.main_stat_options:
            possible_stats = self.data_manager.main_stat_options[cost]
        else:
            for stats in self.data_manager.main_stat_options.values():
                possible_stats.extend(stats)
            possible_stats = list(set(possible_stats))

        stat_aliases = self.data_manager.stat_aliases

        cleaned_lines = []
        for line in ocr_text.splitlines():
            line_clean = line.strip()
            if not line_clean:
                continue
            line_clean = re.sub(r"^\s*[\・\.\:\*]\s*", "", line_clean)
            line_clean = re.sub(r"\s+", " ", line_clean)
            line_clean = re.sub(r"(\d)\s*%", r"\1%", line_clean)
            cleaned_lines.append(line_clean)

        search_limit = min(len(cleaned_lines), 10)
        search_lines = cleaned_lines[:search_limit]

        for line in search_lines:
            for stat in possible_stats:
                if stat in line:
                    return stat

                aliases = stat_aliases.get(stat, [])
                for alias in aliases:
                    if alias in line:
                        return stat

                if stat.endswith("%"):
                    base_name = stat.rstrip("%")
                    if base_name in line:
                        return stat
        return None

    def parse_substats(self, ocr_text: str, language: str) -> Tuple[List[SubStat], List[str]]:
        """Parses substats from OCR text."""
        if not ocr_text or not ocr_text.strip():
            return [], []

        cleaned_lines = []
        for line in ocr_text.strip().splitlines():
            if not line.strip():
                continue
            cleaned_line = re.sub(r"^\s*[\・\.]*\s*", "", line.strip())
            cleaned_line = re.sub(r"\s+", " ", cleaned_line)
            cleaned_line = re.sub(r"(\d)\s*%", r"\1%", cleaned_line)
            cleaned_lines.append(cleaned_line.strip())

        lines = cleaned_lines
        last_five = lines[-5:] if len(lines) >= 5 else lines
        alias_pairs = self.data_manager.get_alias_pairs()

        found_substats = []
        log_messages = []

        for i, line in enumerate(last_five):
            result = self._parse_single_line(line, alias_pairs)
            if result:
                substat, is_percent = result
                found_substats.append(substat)
                stat_name_for_log = self.tr(substat.stat)
                log_messages.append(
                    f"OCR auto-fill: Sub{i + 1} -> {stat_name_for_log} {substat.value}{'%' if is_percent else ''}"
                )

        return found_substats, log_messages

    def _parse_single_line(self, line: str, alias_pairs: List[Tuple[str, str]]) -> Optional[Tuple[SubStat, bool]]:
        stat_found = ""
        num_found = ""
        is_percent = False

        match = re.search(r"(.+?)\s+([\d\.]*\d[\d\.]*(?:\s*[%％])?)", line)
        if match:
            stat_text_from_line = match.group(1).strip()
            num_text_from_line = match.group(2).strip()
            for stat, alias in alias_pairs:
                if stat_text_from_line == stat or stat_text_from_line == alias:
                    stat_found = stat
                    nums = re.findall(r"[\d\.]*\d[\d\.]*", num_text_from_line.replace("％", "%"))
                    if nums:
                        num_found = nums[0]
                        if "%" in num_text_from_line or "％" in num_text_from_line:
                            is_percent = True
                    break

        if not stat_found:
            for stat, alias in alias_pairs:
                if alias in line:
                    stat_found = stat
                    nums = re.findall(r"[\d\.]*\d[\d\.]*", line.replace("％", "%"))
                    if nums:
                        num_found = nums[0]
                        if "%" in line or "％" in line:
                            is_percent = True
                    break

        if stat_found and num_found:
            corrected_stat, corrected_val, was_percent = self.validate_and_correct_substat(
                stat_found, num_found, is_percent
            )
            return SubStat(stat=corrected_stat, value=corrected_val), was_percent
        return None

    def validate_and_correct_substat(self, stat_name: str, raw_value: str, is_percent: bool) -> Tuple[str, str, bool]:
        try:
            val = float(raw_value)
        except ValueError:
            return stat_name, raw_value, is_percent

        search_name = stat_name if stat_name in self.data_manager.substat_max_values else f"{stat_name}%"
        max_val = self.data_manager.substat_max_values.get(search_name)
        if not max_val:
            return stat_name, raw_value, is_percent

        if stat_name in ["攻撃力", "HP", "防御力"]:
            if not is_percent and val < 20.0:
                is_percent = True
                stat_name = f"{stat_name}%"
            elif is_percent and val > 20.0:
                is_percent = False
                stat_name = stat_name.replace("%", "")

        if val > max_val * 1.5:
            new_val = val / 10.0
            if new_val <= max_val * 1.1:
                val = new_val

        formatted_val = f"{val:.1f}" if is_percent or "." in raw_value else str(int(val))
        return stat_name, formatted_val, is_percent

    def detect_cost(self, ocr_text: str) -> Optional[str]:
        if not ocr_text:
            return None
        lines = [line.strip() for line in ocr_text.splitlines() if line.strip()]
        if not lines:
            return None

        check_count = min(len(lines), 3)
        cost_pattern = re.compile(r"(?:COST|Cost|cost|コスト)[\s:.]*([134])")
        for i in range(check_count):
            line = lines[i]
            match = cost_pattern.search(line)
            if match:
                return match.group(1)
        return None
