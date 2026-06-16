"""
tests/test_tools.py

Tests for the three FitFindr tools in tools.py. Covers the happy path and
the documented failure mode for each tool (see planning.md's Error Handling
table). suggest_outfit and create_fit_card hit the real Groq API, so these
require a valid GROQ_API_KEY in .env to pass.
"""

import pytest

from tools import search_listings, suggest_outfit, create_fit_card
from utils.data_loader import get_example_wardrobe, get_empty_wardrobe


# ── search_listings ─────────────────────────────────────────────────────────

def test_search_returns_results():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert isinstance(results, list)
    assert len(results) > 0


def test_search_empty_results():
    results = search_listings("designer ballgown", size="XXS", max_price=5)
    assert results == []  # empty list, no exception


def test_search_price_filter():
    results = search_listings("jacket", size=None, max_price=10)
    assert all(item["price"] <= 10 for item in results)


def test_search_size_filter():
    results = search_listings("track jacket", size="M", max_price=None)
    assert len(results) > 0
    assert all("m" in item["size"].lower() for item in results)


def test_search_results_sorted_best_match_first():
    results = search_listings("vintage graphic tee", size=None, max_price=30)
    assert len(results) > 1
    # The top result should mention "graphic tee" more directly than the rest —
    # spot check that the literal "Graphic Tee" listing ranks first.
    assert "graphic tee" in results[0]["title"].lower()


def test_search_does_not_raise_on_no_matches():
    # Should return [] cleanly, never raise, even for nonsense queries.
    results = search_listings("xyzzy nonexistent item", size=None, max_price=None)
    assert results == []


# ── suggest_outfit ───────────────────────────────────────────────────────────

def test_suggest_outfit_with_wardrobe_returns_nonempty_string():
    item = search_listings("vintage graphic tee", max_price=30)[0]
    outfit = suggest_outfit(item, get_example_wardrobe())
    assert isinstance(outfit, str)
    assert len(outfit.strip()) > 0


def test_suggest_outfit_empty_wardrobe_does_not_crash():
    item = search_listings("vintage graphic tee", max_price=30)[0]
    outfit = suggest_outfit(item, get_empty_wardrobe())
    assert isinstance(outfit, str)
    assert len(outfit.strip()) > 0  # falls back to general styling advice


def test_suggest_outfit_handles_missing_wardrobe_key_gracefully():
    item = search_listings("vintage graphic tee", max_price=30)[0]
    # A malformed/empty wardrobe dict (no "items" key at all) should not crash.
    outfit = suggest_outfit(item, {})
    assert isinstance(outfit, str)
    assert len(outfit.strip()) > 0


# ── create_fit_card ──────────────────────────────────────────────────────────

def test_create_fit_card_returns_nonempty_string():
    item = search_listings("vintage graphic tee", max_price=30)[0]
    outfit = "Pair this with baggy jeans and chunky sneakers for a 90s grunge look."
    card = create_fit_card(outfit, item)
    assert isinstance(card, str)
    assert len(card.strip()) > 0


def test_create_fit_card_empty_outfit_returns_message_not_exception():
    item = search_listings("vintage graphic tee", max_price=30)[0]
    card = create_fit_card("", item)
    assert isinstance(card, str)
    assert len(card.strip()) > 0
    assert "outfit" in card.lower()  # explains what's missing


def test_create_fit_card_whitespace_only_outfit_treated_as_empty():
    item = search_listings("vintage graphic tee", max_price=30)[0]
    card = create_fit_card("   \n  ", item)
    assert isinstance(card, str)
    assert "suggest_outfit" in card.lower()


def test_create_fit_card_varies_across_calls():
    item = search_listings("vintage graphic tee", max_price=30)[0]
    outfit = "Pair this with baggy jeans and chunky sneakers for a 90s grunge look."
    card_a = create_fit_card(outfit, item)
    card_b = create_fit_card(outfit, item)
    assert card_a != card_b  # higher temperature should produce different phrasing
