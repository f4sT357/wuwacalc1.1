from core.scoring.methods import (
    NormalizedScoring,
    RatioScoring,
    RollQualityScoring,
    EffectiveStatsScoring,
    CVScoring
)

SCORING_METHODS = [
    NormalizedScoring(),
    RatioScoring(),
    RollQualityScoring(),
    EffectiveStatsScoring(),
    CVScoring()
]

def get_scoring_method(name: str):
    for method in SCORING_METHODS:
        if method.name() == name:
            return method
    return None
