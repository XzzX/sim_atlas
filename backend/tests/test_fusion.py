"""Unit tests for weighted reciprocal rank fusion."""

from __future__ import annotations

import pytest

from sim_atlas.fusion import reciprocal_rank_fusion


def _order(fused: dict[str, float]) -> list[str]:
    return sorted(fused, key=lambda node_id: fused[node_id], reverse=True)


def test_single_leg_keeps_its_order() -> None:
    fused = reciprocal_rank_fusion([(1.0, {"a": 0.1, "b": 0.9, "c": 0.5})])
    assert _order(fused) == ["b", "c", "a"]


def test_rrf_score_of_a_single_leg() -> None:
    fused = reciprocal_rank_fusion([(1.0, {"a": 2.0, "b": 1.0})], k=60)
    assert fused["a"] == pytest.approx(1 / 61)
    assert fused["b"] == pytest.approx(1 / 62)


def test_found_by_two_legs_outranks_found_by_one() -> None:
    """Agreement between legs beats a single leg's top spot."""
    fused = reciprocal_rank_fusion(
        [
            (1.0, {"solo": 9.0, "both": 1.0}),
            (1.0, {"both": 1.0}),
        ]
    )
    assert _order(fused) == ["both", "solo"]


def test_absent_from_a_leg_contributes_nothing() -> None:
    fused = reciprocal_rank_fusion([(1.0, {"a": 1.0}), (1.0, {"b": 1.0})])
    assert fused["a"] == pytest.approx(fused["b"])
    assert set(fused) == {"a", "b"}


def test_weights_decide_between_conflicting_legs() -> None:
    legs_heavy_first = [(2.0, {"x": 2.0, "y": 1.0}), (1.0, {"y": 2.0, "x": 1.0})]
    legs_heavy_second = [(1.0, {"x": 2.0, "y": 1.0}), (2.0, {"y": 2.0, "x": 1.0})]
    assert _order(reciprocal_rank_fusion(legs_heavy_first)) == ["x", "y"]
    assert _order(reciprocal_rank_fusion(legs_heavy_second)) == ["y", "x"]


def test_weights_are_renormalised_over_the_legs_passed() -> None:
    """A missing leg must not shrink the scale of the fused scores."""
    one_leg = reciprocal_rank_fusion([(0.5, {"a": 1.0})], k=60)
    two_legs = reciprocal_rank_fusion([(1.0, {"a": 1.0}), (3.0, {"a": 1.0})], k=60)
    assert one_leg["a"] == pytest.approx(1 / 61)
    assert two_legs["a"] == pytest.approx(1 / 61)


def test_ties_keep_insertion_order() -> None:
    fused = reciprocal_rank_fusion([(1.0, {"first": 1.0, "second": 1.0})])
    assert _order(fused) == ["first", "second"]


def test_no_legs_fuse_to_nothing() -> None:
    assert reciprocal_rank_fusion([]) == {}


def test_empty_legs_fuse_to_nothing() -> None:
    assert reciprocal_rank_fusion([(1.0, {}), (1.0, {})]) == {}
