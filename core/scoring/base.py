from abc import ABC, abstractmethod
from typing import Dict, Any

class ScoringStrategy(ABC):
    """Abstract base class for all echo scoring methodologies."""
    
    @abstractmethod
    def name(self) -> str:
        """Returns the internal key for this scoring method (e.g., 'normalized')."""
        pass

    @abstractmethod
    def calculate(self, echo: Any, stat_weights: Dict[str, float], config: Dict[str, Any]) -> float:
        """Performs calculation and returns a numeric score."""
        pass
