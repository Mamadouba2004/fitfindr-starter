"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import os

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.

    Args:
        description: Keywords describing what the user is looking for
                     (e.g., "vintage graphic tee").
        size:        Size string to filter by, or None to skip size filtering.
                     Matching is case-insensitive (e.g., "M" matches "S/M").
        max_price:   Maximum price (inclusive), or None to skip price filtering.

    Returns:
        A list of matching listing dicts, sorted by relevance (best match first).
        Returns an empty list if nothing matches — does NOT raise an exception.

    Each listing dict has the following fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand, platform

    TODO:
        1. Load all listings with load_listings().
        2. Filter by max_price and size (if provided).
        3. Score each remaining listing by keyword overlap with `description`.
        4. Drop any listings with a score of 0 (no relevant matches).
        5. Sort by score, highest first, and return the listing dicts.

    Before writing code, fill in the Tool 1 section of planning.md.
    """
    listings = load_listings()

    # Filter by max_price (inclusive) and size (case-insensitive substring match)
    candidates = []
    for listing in listings:
        if max_price is not None and listing["price"] > max_price:
            continue
        if size is not None and size.strip().lower() not in listing["size"].lower():
            continue
        candidates.append(listing)

    # Score by keyword overlap between `description` and the listing's
    # title, description, category, and style_tags. A handful of words
    # (e.g. "vintage", "classic") appear on most listings' style_tags and
    # are too generic to indicate a real match on their own — they're
    # downweighted so an item only surfaces if it also matches something
    # more specific (what the item actually is), not just its general era/vibe.
    _STOPWORDS = {"a", "an", "the", "for", "and", "or", "in", "with", "of"}
    _GENERIC_TAGS = {
        "vintage", "classic", "basics", "minimal", "earth tones",
        "streetwear", "layering", "oversized",
    }
    keywords = [w for w in description.lower().split() if w and w not in _STOPWORDS]

    def _score(listing: dict) -> float:
        title_words = listing["title"].lower()
        tags = [tag.lower() for tag in listing["style_tags"]]
        specific_tags = " ".join(t for t in tags if t not in _GENERIC_TAGS)
        generic_tags = " ".join(t for t in tags if t in _GENERIC_TAGS)
        desc_words = listing["description"].lower()
        category_word = listing["category"].lower()

        score = 0.0
        for kw in keywords:
            if kw in title_words:
                score += 3
            if kw in specific_tags or kw in category_word:
                score += 2
            if kw in generic_tags:
                score += 0.5
            if kw in desc_words:
                score += 1
        return score

    # Require a real match — title, category, or a specific style tag —
    # not just a generic vibe word shared by most of the dataset. This is
    # what keeps a search for "vintage graphic tee" from also surfacing a
    # "vintage" leather belt that has nothing to do with tees.
    MIN_SCORE = 2
    scored = [(listing, _score(listing)) for listing in candidates]
    scored = [(listing, score) for listing, score in scored if score >= MIN_SCORE]
    scored.sort(key=lambda pair: pair[1], reverse=True)

    return [listing for listing, _ in scored]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.

    Args:
        new_item: A listing dict (the item the user is considering buying).
        wardrobe: A wardrobe dict with an 'items' key containing a list of
                  wardrobe item dicts. May be empty — handle this gracefully.

    Returns:
        A non-empty string with outfit suggestions.
        If the wardrobe is empty, offer general styling advice for the item
        rather than raising an exception or returning an empty string.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If empty: call the LLM with a prompt for general styling ideas
           (what kinds of items pair well, what vibe it suits, etc.).
        3. If not empty: format the wardrobe items into a prompt and ask
           the LLM to suggest specific outfit combinations using the new item
           and named pieces from the wardrobe.
        4. Return the LLM's response as a string.

    Before writing code, fill in the Tool 2 section of planning.md.
    """
    item_desc = (
        f"{new_item.get('title', 'this item')} "
        f"({', '.join(new_item.get('style_tags', [])) or 'no style tags'}, "
        f"colors: {', '.join(new_item.get('colors', [])) or 'unknown'})"
    )

    wardrobe_items = wardrobe.get("items", []) if wardrobe else []

    if not wardrobe_items:
        prompt = (
            f"A user is considering buying this thrifted item: {item_desc}. "
            "They haven't entered a wardrobe yet, so give general styling advice: "
            "what kinds of pieces would pair well with it (by category/color/vibe), "
            "and what overall look or aesthetic it suits. "
            "Start your response by briefly noting this is general advice since "
            "no wardrobe was found. Keep it to 2-4 sentences, written casually."
        )
    else:
        wardrobe_lines = "\n".join(
            f"- {w['name']} ({', '.join(w.get('style_tags', []))})"
            for w in wardrobe_items
        )
        prompt = (
            f"A user is considering buying this thrifted item: {item_desc}.\n\n"
            f"Here is their current wardrobe:\n{wardrobe_lines}\n\n"
            "Suggest 1-2 complete outfit combinations that pair the new item with "
            "specific pieces from their wardrobe (refer to them by name). "
            "Include a short styling tip (how to wear/fit it). "
            "Keep it to 2-4 sentences, written casually, like advice from a friend."
        )

    try:
        client = _get_groq_client()
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=200,
        )
        result = response.choices[0].message.content.strip()
        if not result:
            raise ValueError("Empty response from LLM")
        return result
    except Exception:
        title = new_item.get("title", "this item")
        price = new_item.get("price", "?")
        platform = new_item.get("platform", "the platform")
        return (
            "Couldn't generate a personalized outfit suggestion right now "
            "(styling service unavailable). Here's the item on its own: "
            f"{title} — ${price} on {platform}."
        )


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.

    Args:
        outfit:   The outfit suggestion string from suggest_outfit().
        new_item: The listing dict for the thrifted item.

    Returns:
        A 2–4 sentence string usable as an Instagram/TikTok caption.
        If outfit is empty or missing, return a descriptive error message
        string — do NOT raise an exception.

    The caption should:
    - Feel casual and authentic (like a real OOTD post, not a product description)
    - Mention the item name, price, and platform naturally (once each)
    - Capture the outfit vibe in specific terms
    - Sound different each time for different inputs (use higher LLM temperature)

    TODO:
        1. Guard against an empty or whitespace-only outfit string.
        2. Build a prompt that gives the LLM the item details and the outfit,
           and asks for a caption matching the style guidelines above.
        3. Call the LLM and return the response.

    Before writing code, fill in the Tool 3 section of planning.md.
    """
    if not outfit or not outfit.strip():
        return (
            "Can't create a fit card without an outfit suggestion — try running "
            "suggest_outfit first, or check that it returned a non-empty result."
        )

    title = new_item.get("title", "this piece")
    price = new_item.get("price", "?")
    platform = new_item.get("platform", "a resale app")

    prompt = (
        f"Write a short, casual Instagram/TikTok OOTD caption for a thrifted "
        f"outfit post. The new piece is: \"{title}\", bought for ${price} on "
        f"{platform}. Here's the styling idea to caption: {outfit}\n\n"
        "Write 2-4 sentences. Mention the item name, the price, and the platform "
        "naturally, each once. Capture the specific vibe of the outfit. "
        "Sound like a real person posting a fit pic, not a product listing — "
        "casual tone, can use lowercase/emoji sparingly, no hashtags block."
    )

    try:
        client = _get_groq_client()
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=1.0,
            max_tokens=150,
        )
        result = response.choices[0].message.content.strip()
        if not result:
            raise ValueError("Empty response from LLM")
        return result
    except Exception:
        return (
            "Couldn't generate a fit card right now (caption service unavailable). "
            f"Here's the basic info: {title} styled as: {outfit}, found for "
            f"${price} on {platform}."
        )
