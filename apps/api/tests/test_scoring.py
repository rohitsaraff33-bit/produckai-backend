"""Test scoring calculations."""

from packages.shared.scoring import (
    ScoreWeights,
    SegmentPriorities,
    calculate_frequency_norm,
    calculate_acv_norm,
    calculate_sentiment_lift,
    calculate_theme_score,
)


def test_frequency_norm():
    """Test frequency normalization."""
    norm = calculate_frequency_norm(10, 15, 20, 30)
    assert 0 <= norm <= 1


def test_acv_norm():
    """Test ACV normalization."""
    norm = calculate_acv_norm(50000, 200000)
    assert 0 <= norm <= 1


def test_sentiment_lift():
    """Test sentiment lift calculation."""
    # Negative sentiment should give higher lift
    lift_neg = calculate_sentiment_lift(-0.5)
    lift_pos = calculate_sentiment_lift(0.5)
    assert lift_neg > lift_pos


def test_theme_score_calculation():
    """Test complete ThemeScore calculation."""
    weights = ScoreWeights()
    seg_priorities = SegmentPriorities()

    components = calculate_theme_score(
        freq_30d=10,
        freq_90d=15,
        acv_sum=100000,
        avg_sentiment=-0.2,
        segment_counts={"ENT": 5, "MM": 3, "SMB": 2},
        weekly_counts=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
        similarity_to_higher=0.0,
        max_freq_30d=20,
        max_freq_90d=30,
        max_acv_sum=200000,
        weights=weights,
        segment_priorities=seg_priorities,
    )

    assert 0 <= components.final_score <= 1
    assert components.frequency_norm >= 0
    assert components.acv_norm >= 0
    assert components.sentiment_lift >= 0
