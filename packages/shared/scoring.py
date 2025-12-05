"""
ThemeScore calculation with transparent, configurable weights.

ThemeScore =
  w_f*F_norm + w_acv*ACV_norm + w_sent*SentimentLift +
  w_seg*SegmentPriority + w_trend*TrendMomentum - w_dup*DupPenalty
"""

import math
from dataclasses import dataclass
from typing import Dict


@dataclass
class ScoreWeights:
    """Configurable weights for ThemeScore components."""

    frequency: float = 0.35
    acv: float = 0.30
    sentiment: float = 0.10
    segment: float = 0.15
    trend: float = 0.10
    duplicate: float = 0.10

    def to_dict(self) -> Dict[str, float]:
        return {
            "frequency": self.frequency,
            "acv": self.acv,
            "sentiment": self.sentiment,
            "segment": self.segment,
            "trend": self.trend,
            "duplicate": self.duplicate,
        }


@dataclass
class SegmentPriorities:
    """Priority multipliers for customer segments."""

    ENT: float = 1.0  # Enterprise
    MM: float = 0.7  # Mid-Market
    SMB: float = 0.5  # Small Business

    def to_dict(self) -> Dict[str, float]:
        return {"ENT": self.ENT, "MM": self.MM, "SMB": self.SMB}


@dataclass
class ThemeScoreComponents:
    """Individual components of ThemeScore for transparency."""

    frequency_norm: float
    acv_norm: float
    sentiment_lift: float
    segment_priority: float
    trend_momentum: float
    dup_penalty: float
    final_score: float

    def to_dict(self) -> Dict[str, float]:
        return {
            "frequency_norm": self.frequency_norm,
            "acv_norm": self.acv_norm,
            "sentiment_lift": self.sentiment_lift,
            "segment_priority": self.segment_priority,
            "trend_momentum": self.trend_momentum,
            "dup_penalty": self.dup_penalty,
            "final_score": self.final_score,
        }


def normalize_min_max(value: float, min_val: float, max_val: float) -> float:
    """Normalize value to [0, 1] using min-max scaling."""
    if max_val == min_val:
        return 0.0
    return max(0.0, min(1.0, (value - min_val) / (max_val - min_val)))


def calculate_frequency_norm(
    count_30d: int, count_90d: int, max_count_30d: int, max_count_90d: int
) -> float:
    """
    Calculate normalized frequency score.

    Exponentially weights recent feedback more heavily:
    - 70% weight to last 30 days
    - 30% weight to 30-90 days

    Args:
        count_30d: Unique account count in last 30 days
        count_90d: Unique account count in last 90 days
        max_count_30d: Max count across all themes (for normalization)
        max_count_90d: Max count across all themes (for normalization)

    Returns:
        Normalized frequency score [0, 1]
    """
    norm_30d = normalize_min_max(count_30d, 0, max(max_count_30d, 1))
    norm_90d = normalize_min_max(count_90d, 0, max(max_count_90d, 1))
    return 0.7 * norm_30d + 0.3 * norm_90d


def calculate_acv_norm(acv_sum: float, max_acv_sum: float) -> float:
    """
    Calculate normalized ACV score using log scaling.

    Log scaling prevents large enterprises from dominating:
    log(1 + acv) / log(1 + max_acv)

    Args:
        acv_sum: Sum of ACV from all customers providing feedback
        max_acv_sum: Max ACV sum across all themes

    Returns:
        Normalized ACV score [0, 1]
    """
    if max_acv_sum <= 0:
        return 0.0
    return math.log(1 + acv_sum) / math.log(1 + max_acv_sum)


def calculate_sentiment_lift(avg_sentiment: float) -> float:
    """
    Calculate sentiment lift (urgency from negativity).

    More negative sentiment = higher urgency = higher score
    Sentiment range: [-1, 1] where -1 is very negative

    Args:
        avg_sentiment: Average sentiment score [-1, 1]

    Returns:
        Sentiment lift [0, 1]
    """
    # Clamp and invert: -1 -> 1, 0 -> 0.5, 1 -> 0
    return max(0.0, min(1.0, (1 - avg_sentiment) / 2))


def calculate_segment_priority(
    segment_counts: Dict[str, int], priorities: SegmentPriorities
) -> float:
    """
    Calculate weighted segment priority.

    Args:
        segment_counts: Dict of {"ENT": 5, "MM": 3, "SMB": 10}
        priorities: Segment priority multipliers

    Returns:
        Weighted average priority [0, 1]
    """
    total_count = sum(segment_counts.values())
    if total_count == 0:
        return 0.0

    priority_dict = priorities.to_dict()
    weighted_sum = sum(
        segment_counts.get(seg, 0) * priority_dict.get(seg, 0.5)
        for seg in ["ENT", "MM", "SMB"]
    )
    return weighted_sum / total_count


def calculate_trend_momentum(weekly_counts: list[int]) -> float:
    """
    Calculate trend momentum using linear regression on weekly counts.

    Positive slope = growing interest = boost
    Negative slope = declining interest = penalty

    Args:
        weekly_counts: List of feedback counts for last N weeks (e.g., 12 weeks)

    Returns:
        Normalized trend momentum [-0.5, 0.5]
    """
    if len(weekly_counts) < 2:
        return 0.0

    n = len(weekly_counts)
    x_vals = list(range(n))
    mean_x = sum(x_vals) / n
    mean_y = sum(weekly_counts) / n

    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(x_vals, weekly_counts))
    denominator = sum((x - mean_x) ** 2 for x in x_vals)

    if denominator == 0:
        return 0.0

    slope = numerator / denominator
    # Normalize to [-0.5, 0.5] range (assuming slope won't exceed ±10)
    return max(-0.5, min(0.5, slope / 20))


def calculate_dup_penalty(similarity_to_higher_scored: float) -> float:
    """
    Calculate duplicate penalty based on similarity to higher-scored themes.

    If a theme is very similar to a higher-ranked theme, penalize it.

    Args:
        similarity_to_higher_scored: Max cosine similarity to any higher-scored theme [0, 1]

    Returns:
        Duplicate penalty [0, 1]
    """
    if similarity_to_higher_scored > 0.85:
        return 0.5 * similarity_to_higher_scored
    return 0.0


def calculate_theme_score(
    freq_30d: int,
    freq_90d: int,
    acv_sum: float,
    avg_sentiment: float,
    segment_counts: Dict[str, int],
    weekly_counts: list[int],
    similarity_to_higher: float,
    max_freq_30d: int,
    max_freq_90d: int,
    max_acv_sum: float,
    weights: ScoreWeights,
    segment_priorities: SegmentPriorities,
) -> ThemeScoreComponents:
    """
    Calculate complete ThemeScore with all components.

    Args:
        freq_30d: Account count in last 30 days
        freq_90d: Account count in last 90 days
        acv_sum: Sum of ACV from feedback accounts
        avg_sentiment: Average sentiment score
        segment_counts: Dict of segment -> count
        weekly_counts: List of weekly feedback counts
        similarity_to_higher: Similarity to highest-scored similar theme
        max_freq_30d: Max frequency across all themes (for normalization)
        max_freq_90d: Max frequency across all themes (for normalization)
        max_acv_sum: Max ACV across all themes (for normalization)
        weights: ScoreWeights instance
        segment_priorities: SegmentPriorities instance

    Returns:
        ThemeScoreComponents with all component values
    """
    f_norm = calculate_frequency_norm(freq_30d, freq_90d, max_freq_30d, max_freq_90d)
    acv_norm = calculate_acv_norm(acv_sum, max_acv_sum)
    sent_lift = calculate_sentiment_lift(avg_sentiment)
    seg_priority = calculate_segment_priority(segment_counts, segment_priorities)
    trend = calculate_trend_momentum(weekly_counts)
    dup_penalty = calculate_dup_penalty(similarity_to_higher)

    final_score = (
        weights.frequency * f_norm
        + weights.acv * acv_norm
        + weights.sentiment * sent_lift
        + weights.segment * seg_priority
        + weights.trend * trend
        - weights.duplicate * dup_penalty
    )

    # Clamp to [0, 1]
    final_score = max(0.0, min(1.0, final_score))

    return ThemeScoreComponents(
        frequency_norm=f_norm,
        acv_norm=acv_norm,
        sentiment_lift=sent_lift,
        segment_priority=seg_priority,
        trend_momentum=trend,
        dup_penalty=dup_penalty,
        final_score=final_score,
    )
