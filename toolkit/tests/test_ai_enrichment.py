import pytest

pytest.importorskip("openai")

from sim_atlas_toolkit.parsers.ai_enrichment import clean_response  # noqa: E402


def test_plain_text_passthrough() -> None:
    assert clean_response("Compute a sum.") == "Compute a sum."


def test_strips_think_block() -> None:
    raw = "<think>Let me reason about this.</think>\n\nCompute a sum."
    assert clean_response(raw) == "Compute a sum."


def test_strips_think_block_case_insensitive_multiline() -> None:
    raw = "<THINK>\nline one\nline two\n</THINK>Compute a sum."
    assert clean_response(raw) == "Compute a sum."


def test_strips_lone_closing_think_tag() -> None:
    # Reasoning models that emit no opening tag.
    raw = "internal reasoning here</think>Compute a sum."
    assert clean_response(raw) == "Compute a sum."


def test_unwraps_code_fence() -> None:
    raw = "```python\nCompute a sum.\n\nArgs:\n    x: the value.\n```"
    assert clean_response(raw) == "Compute a sum.\n\nArgs:\n    x: the value."


def test_unwraps_triple_quotes() -> None:
    assert clean_response('"""Compute a sum."""') == "Compute a sum."


def test_combined_think_and_fence() -> None:
    raw = "<think>reason</think>\n```\nCompute a sum.\n```"
    assert clean_response(raw) == "Compute a sum."


def test_single_quote_char_not_overstripped() -> None:
    assert clean_response('"') == '"'
