"""Unit tests for weighted reciprocal rank fusion."""

from __future__ import annotations

import pytest

from sim_atlas.fusion import Leg, reciprocal_rank_fusion


def _order(fused: dict[str, float]) -> list[str]:
    return sorted(fused, key=lambda node_id: fused[node_id], reverse=True)


def test_single_leg_keeps_its_order() -> None:
    fused = reciprocal_rank_fusion([Leg(1.0, {"a": 0.1, "b": 0.9, "c": 0.5})])
    assert _order(fused) == ["b", "c", "a"]


def test_rrf_score_of_a_single_leg() -> None:
    fused = reciprocal_rank_fusion([Leg(1.0, {"a": 2.0, "b": 1.0})], k=60)
    assert fused["a"] == pytest.approx(1 / 61)
    assert fused["b"] == pytest.approx(1 / 62)


def test_found_by_two_legs_outranks_found_by_one() -> None:
    """Agreement between legs beats a single leg's top spot."""
    fused = reciprocal_rank_fusion(
        [Leg(1.0, {"solo": 9.0, "both": 1.0}), Leg(1.0, {"both": 1.0})]
    )
    assert _order(fused) == ["both", "solo"]


def test_absent_from_a_full_leg_contributes_nothing() -> None:
    fused = reciprocal_rank_fusion([Leg(1.0, {"a": 1.0}), Leg(1.0, {"b": 1.0})])
    assert fused["a"] == pytest.approx(fused["b"])
    assert set(fused) == {"a", "b"}


def test_weights_decide_between_conflicting_legs() -> None:
    first_heavy = [Leg(2.0, {"x": 2.0, "y": 1.0}), Leg(1.0, {"y": 2.0, "x": 1.0})]
    second_heavy = [Leg(1.0, {"x": 2.0, "y": 1.0}), Leg(2.0, {"y": 2.0, "x": 1.0})]
    assert _order(reciprocal_rank_fusion(first_heavy)) == ["x", "y"]
    assert _order(reciprocal_rank_fusion(second_heavy)) == ["y", "x"]


def test_ties_share_a_rank() -> None:
    """A leg that cannot tell two nodes apart must not pick one by order."""
    fused = reciprocal_rank_fusion(
        [Leg(1.0, {"first": 1.0, "second": 1.0}), Leg(0.5, {"second": 1.0})]
    )
    assert _order(fused) == ["second", "first"]


def test_ties_after_a_leader_rank_by_competition() -> None:
    fused = reciprocal_rank_fusion([Leg(1.0, {"a": 3.0, "b": 1.0, "c": 1.0})], k=60)
    assert fused["b"] == pytest.approx(1 / 62)
    assert fused["c"] == pytest.approx(1 / 62)


def test_weights_are_renormalised_over_the_legs_passed() -> None:
    """A missing leg must not shrink the scale of the fused scores."""
    one_leg = reciprocal_rank_fusion([Leg(0.5, {"a": 1.0})], k=60)
    two_legs = reciprocal_rank_fusion([Leg(1.0, {"a": 1.0}), Leg(3.0, {"a": 1.0})])
    assert one_leg["a"] == pytest.approx(1 / 61)
    assert two_legs["a"] == pytest.approx(1 / 61)


def test_absence_from_a_partial_leg_is_no_opinion() -> None:
    """An unembedded node is fused as if the semantic leg had not run."""
    fused = reciprocal_rank_fusion(
        [
            Leg(1.0, {"unembedded": 1.0, "embedded": 0.5}),
            Leg(1.0, {"embedded": 1.0}, partial=True),
        ],
        k=60,
    )
    assert fused["unembedded"] == pytest.approx(1 / 61)
    assert fused["embedded"] == pytest.approx((1 / 62 + 1 / 61) / 2)
    assert _order(fused) == ["unembedded", "embedded"]


def test_a_low_rank_in_a_partial_leg_still_counts_against_a_node() -> None:
    """Holding a node is an opinion: a poor semantic rank dilutes it."""
    lexical = {"a": 1.0, "b": 1.0}
    semantic = {"x": 1.0, **{f"n{i}": 0.9 for i in range(50)}, "b": 0.0}
    fused = reciprocal_rank_fusion(
        [Leg(1.0, lexical), Leg(1.0, semantic, partial=True)]
    )
    assert fused["a"] > fused["b"]


def test_no_legs_fuse_to_nothing() -> None:
    assert reciprocal_rank_fusion([]) == {}


def test_empty_legs_fuse_to_nothing() -> None:
    assert reciprocal_rank_fusion([Leg(1.0, {}), Leg(1.0, {}, partial=True)]) == {}
