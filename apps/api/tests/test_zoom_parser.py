"""Tests for Zoom VTT parser."""

import pytest
from apps.api.services.zoom_client import parse_vtt_transcript, _vtt_time_to_seconds


def test_vtt_time_to_seconds():
    """Test VTT time parsing to seconds."""
    assert _vtt_time_to_seconds('00:00:05.120') == pytest.approx(5.120, rel=0.01)
    assert _vtt_time_to_seconds('00:01:30.000') == pytest.approx(90.0, rel=0.01)
    assert _vtt_time_to_seconds('01:15:45.500') == pytest.approx(4545.5, rel=0.01)


def test_parse_vtt_transcript():
    """Test parsing VTT transcript content."""
    vtt_content = """WEBVTT

00:00:02.120 --> 00:00:05.890
<v Sarah Chen>Thanks everyone for joining.

00:00:06.120 --> 00:00:10.450
<v Sarah Chen>Today we're talking about feedback.

00:00:11.230 --> 00:00:14.560
<v David Martinez>Happy to be here.
"""

    segments = parse_vtt_transcript(vtt_content)

    assert len(segments) == 3

    # Check first segment
    assert segments[0]['speaker'] == 'Sarah Chen'
    assert segments[0]['text'] == 'Thanks everyone for joining.'
    assert segments[0]['start_time'] == '00:00:02.120'
    assert segments[0]['end_time'] == '00:00:05.890'
    assert segments[0]['start_seconds'] == pytest.approx(2.120, rel=0.01)

    # Check third segment (different speaker)
    assert segments[2]['speaker'] == 'David Martinez'
    assert segments[2]['text'] == 'Happy to be here.'


def test_parse_vtt_transcript_no_speaker():
    """Test parsing VTT transcript without speaker tags."""
    vtt_content = """WEBVTT

00:00:02.120 --> 00:00:05.890
Thanks everyone for joining.

00:00:06.120 --> 00:00:10.450
Today we're talking about feedback.
"""

    segments = parse_vtt_transcript(vtt_content)

    assert len(segments) == 2
    assert segments[0]['speaker'] == 'Unknown'
    assert segments[0]['text'] == 'Thanks everyone for joining.'


def test_parse_empty_vtt():
    """Test parsing empty VTT content."""
    vtt_content = """WEBVTT
"""

    segments = parse_vtt_transcript(vtt_content)
    assert len(segments) == 0
