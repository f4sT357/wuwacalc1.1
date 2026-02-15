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

        # Detailed recognition logs
        if cost:
            log_messages.append(f"OCR Detected: Cost -> {cost}")
        if main_stat:
            log_messages.append(f"OCR Detected: Main Stat -> {self.tr(main_stat)}")
        
        log_messages.append(f"OCR Detected: {len(substats)} Substats")

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

    NUMERIC_CLEANING_MAP = {
        'B': '8',
        'S': '5',
        'O': '0',
        'o': '0',
        'I': '1',
        '|': '1',
        'l': '1',
        '!': '1',
        'g': '9',
        'q': '9',
        '(': '1',
        ')': '1',
    }

    def _clean_numeric_string(self, text: str) -> str:
        """Clean common OCR misidentifications and handle decimal delimiters."""
        if not text:
            return ""
        
        # 1. First pass: map common misreads and treat certain chars as potential decimal points
        temp = []
        for char in text:
            if char.isdigit() or char == '.':
                temp.append(char)
            elif char in self.NUMERIC_CLEANING_MAP:
                temp.append(self.NUMERIC_CLEANING_MAP[char])
            elif char in [',', ':', ';']:
                temp.append('.')
        
        cleaned = "".join(temp)
        
        # 2. Extract only the valid numeric part (digits and dots)
        # We want to ignore leading/trailing non-numeric noise that might have survived
        # and ensure we only have one decimal point.
        match = re.search(r'(\d*\.?\d+)', cleaned)
        if not match:
            return ""
        
        val_str = match.group(1).strip('.')
        
        # Handle cases with multiple dots (e.g. "1.3.8" -> "13.8")
        if val_str.count('.') > 1:
            parts = val_str.split('.')
            # Keep the last dot as the decimal if it looks like a WuWa substat (usually 1 decimal place)
            val_str = "".join(parts[:-1]) + "." + parts[-1]
            
        return val_str

    def _parse_single_line(self, line: str, alias_pairs: List[Tuple[str, str]]) -> Optional[Tuple[SubStat, bool]]:
        # Pre-clean line for common artifacts like bullets or decorative dashes
        line_clean = re.sub(r'^[\|｜・°º«»〝〟"\'‘\-\s•]+', "", line.strip())
        line_clean = re.sub(r'[\|｜°º«»〝〟"\'‘]+', " ", line_clean)

        stat_found = ""
        num_found = ""
        is_percent = False

        # Strategy 1: Look for "StatName [Gap] Value"
        # We try to find the longest alias that exists in the line
        best_alias = None
        best_stat = None
        for stat, alias in alias_pairs:
            if alias in line_clean:
                if best_alias is None or len(alias) > len(best_alias):
                    best_alias = alias
                    best_stat = stat

        if best_stat:
            stat_found = best_stat
            # Find the numeric part AFTER the alias
            parts = line_clean.split(best_alias, 1)
            search_area = parts[1] if len(parts) > 1 else line_clean
            
            num_found = self._clean_numeric_string(search_area)
            if "%" in search_area or "％" in search_area:
                is_percent = True
            
            # If no number found after name, try the whole line (fallback)
            if not num_found:
                num_found = self._clean_numeric_string(line_clean)

        if stat_found and num_found:
            corrected_stat, corrected_val, was_percent = self.validate_and_correct_substat(
                stat_found, num_found, is_percent
            )
            if corrected_stat:
                return SubStat(stat=corrected_stat, value=corrected_val), was_percent
        return None

    def validate_and_correct_substat(self, stat_name: str, raw_value: str, is_percent: bool) -> Tuple[str, str, bool]:
        try:
            val = float(raw_value)
        except ValueError:
            return stat_name, raw_value, is_percent

        # Context-aware Correction: HP/ATK/DEF can be Flat or Percent
        # In WuWa, flat stats are much larger than percentage stats.
        # Percentage stats are usually < 15.0%. Flat ATK/DEF are up to 70. Flat HP is up to 580.
        
        base_name = stat_name.replace("%", "")
        if base_name in ["攻撃力", "HP", "防御力"]:
            # If it looks like a percentage but marked as flat (or vice-versa)
            if val < 20.0 and not is_percent:
                is_percent = True
                stat_name = f"{base_name}%"
            elif val > 20.0 and is_percent:
                # 20.0% is a safe threshold as no % stat exceeds ~15%
                is_percent = False
                stat_name = base_name

        # Range Validation: check if value is within plausible bounds (max * 1.5)
        search_name = stat_name if stat_name.endswith("%") else (stat_name if stat_name in self.data_manager.substat_max_values else f"{stat_name}%")
        max_val = self.data_manager.substat_max_values.get(search_name)
        
        if max_val:
            # If OCR read 138 instead of 13.8
            if val > max_val * 2.0:
                if val / 10.0 <= max_val * 1.2:
                    val = val / 10.0
                elif val / 100.0 <= max_val * 1.2:
                    val = val / 100.0

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
