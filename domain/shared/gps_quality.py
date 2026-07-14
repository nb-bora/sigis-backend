"""Scoring qualité GPS pour détection fraude."""

from enum import StrEnum


class GpsScore(StrEnum):
    """Score qualité GPS basé accuracy_m."""

    EXCELLENT = "excellent"  # ≤ 5m
    GOOD = "good"  # 5–25m
    FAIR = "fair"  # 25–100m
    POOR = "poor"  # > 100m


def score_gps_accuracy(accuracy_m: float | None) -> GpsScore:
    """Score qualité GPS.

    Defaults à FAIR si absent.
    """
    if accuracy_m is None:
        return GpsScore.FAIR

    if accuracy_m <= 5:
        return GpsScore.EXCELLENT
    elif accuracy_m <= 25:
        return GpsScore.GOOD
    elif accuracy_m <= 100:
        return GpsScore.FAIR
    else:
        return GpsScore.POOR
