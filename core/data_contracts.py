from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from PIL import Image


@dataclass
class SubStat:
    """Represents a single substat with its name and raw value."""

    stat: str
    value: str
    box: Optional[Tuple[int, int, int, int]] = None # (x, y, w, h)


@dataclass
class OCRResult:
    """Container for the results of an OCR operation on a single image."""

    substats: List[SubStat]
    log_messages: List[str]
    cost: Optional[str]
    main_stat: Optional[str]
    raw_text: str
    boxes: Dict[str, Tuple[int, int, int, int]] = field(default_factory=dict) # General boxes (Main, Cost etc)


@dataclass
class BatchItemResult:
    """Data structure for passing OCR results from worker thread to UI."""

    file_path: str
    result: OCRResult
    original_image: "Image.Image"
    cropped_image: "Image.Image"


@dataclass
class CropConfig:
    """Container for image cropping parameters."""

    mode: str
    left_p: float
    top_p: float
    width_p: float
    height_p: float


@dataclass
class EvaluationResult:
    """Structure for the output of an Echo score evaluation."""

    total_score: float
    effective_count: int
    recommendation: str
    rating: str
    individual_scores: Dict[str, float]
    estimated_stats: Dict[str, float] = field(default_factory=dict) # New: Resulting stats (Echo + Offsets)
    comparison_diff: Optional[float] = None # New: Score difference compared to equipped echo
    consistency_advice: str = "" # New: Advice about main stat consistency
    advice_list: List[str] = field(default_factory=list) # New: List of build optimization advice

@dataclass
class TabImageData:
    """Stored image data for a specific tab."""

    original: "Image.Image"
    cropped: "Image.Image"


@dataclass
class TabResultData:
    """Stored HTML result for a specific tab."""

    content: str


@dataclass
class EchoEntry:
    """Represents the extracted data of an Echo from the UI."""

    tab_index: int
    cost: Optional[str] = None
    main_stat: Optional[str] = None
    substats: List[SubStat] = field(default_factory=list)


@dataclass
class HistoryEntry:
    """Represents a single record in the application history."""

    timestamp: str  # YYYY-MM-DD HH:MM:SS
    character: str  # e.g., "Jinhsi"
    cost: str  # e.g., "4"
    action: str  # e.g., "OCR", "Single Score"
    result: str  # Short summary or score result
    fingerprint: str = ""  # Unique hash of stats
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CharacterProfile:
    """Full settings profile for a character."""

    internal_name: str
    jp_name: str
    cost_config: str
    main_stats: Dict[str, Any]
    weights: Dict[str, float]
    stat_offsets: Dict[str, float] = field(default_factory=dict)
    base_stats: Dict[str, float] = field(default_factory=dict)  # New: Base values (Char + Weapon)
    ideal_stats: Dict[str, float] = field(default_factory=dict)  # New: Target values to achieve
    scaling_stat: str = "攻撃力"  # New: Primary stat (ATK, DEF, or HP)
    element: str = "電導"  # New: Character element (焦熱, 凝縮, 回折, 消滅, 電導, 気動)


class DataLoadError(Exception):
    """Raised when data loading fails."""

    pass
