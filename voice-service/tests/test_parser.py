import pytest

from lectra_voice.models import PauseSegment, SpeechSegment
from lectra_voice.parser import NarrationParseError, parse_narration


BASE = """---
lectra_schema: "1.0"
title: Test talk
language: en-US
default_pace: normal
default_tone: explanatory
---
"""


def test_metadata_never_becomes_speech():
    doc = BASE + """
<!-- slide: 1 -->
# Slide 1: Never speak this heading

Good afternoon everyone.

<!-- pause: medium -->
<!-- tone: serious -->
<!-- private_note: never speak this either -->

- Never speak this bullet.

This is the only other sentence that should be spoken.

```text
Never speak this code block.
```
"""
    parsed = parse_narration(doc)
    spoken = [s.text for s in parsed.segments if isinstance(s, SpeechSegment)]
    assert spoken == [
        "Good afternoon everyone.",
        "This is the only other sentence that should be spoken.",
    ]
    joined = " ".join(spoken)
    assert "Slide 1" not in joined
    assert "private_note" not in joined
    assert "bullet" not in joined
    assert "code block" not in joined


def test_pause_and_state_are_explicit_segments():
    doc = BASE + """
<!-- slide: 1 -->

First sentence.

<!-- pace: slow -->
<!-- tone: reflective -->
<!-- pause: short -->

Second sentence.

<!-- slide: 2 -->

Third sentence.
"""
    parsed = parse_narration(doc)
    assert isinstance(parsed.segments[0], SpeechSegment)
    assert parsed.segments[0].pace == "normal"
    assert isinstance(parsed.segments[1], PauseSegment)
    assert parsed.segments[1].duration_ms == 300
    assert isinstance(parsed.segments[2], SpeechSegment)
    assert parsed.segments[2].pace == "slow"
    assert parsed.segments[2].tone == "reflective"
    assert parsed.segments[2].slide == 1
    assert parsed.segments[3].slide == 2


def test_rejects_unsupported_schema():
    doc = BASE.replace('lectra_schema: "1.0"', 'lectra_schema: "2.0"') + """
<!-- slide: 1 -->

Hello.
"""
    with pytest.raises(NarrationParseError):
        parse_narration(doc)


def test_rejects_non_increasing_slide_numbers():
    doc = BASE + """
<!-- slide: 2 -->

Hello.

<!-- slide: 2 -->

Again.
"""
    with pytest.raises(NarrationParseError):
        parse_narration(doc)
