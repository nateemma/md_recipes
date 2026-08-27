"""Recipe[] -> recipes.json.

One artifact serving both the search page and any machine reader
(see contracts/recipes-json.md).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .model import Recipe


def recipe_entry(recipe: Recipe) -> dict[str, Any]:
    return {
        "slug": recipe.slug,
        "url": recipe.url,
        "title": recipe.title,
        "summary": recipe.summary,
        "category": recipe.category,
        "cuisine": recipe.cuisine,
        "tags": recipe.tags,
        "authors": recipe.authors,
        "servings": recipe.servings,
        "total_time": recipe.total_time_raw,
        "time_min": recipe.total_time.min_minutes if recipe.total_time else None,
        "time_max": recipe.total_time.max_minutes if recipe.total_time else None,
        # Grouped form retained: schema.org has nowhere for it, this does.
        # Prose lines are excluded -- a wrapped sentence fragment is not an
        # ingredient, and including it would produce false ingredient matches.
        "ingredients": [
            {"label": g.label, "items": g.items}
            for g in recipe.ingredients
            if g.items
        ],
    }


def build_index(recipes: list[Recipe]) -> dict[str, Any]:
    return {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "count": len(recipes),
        "categories": sorted({r.category for r in recipes if r.category}),
        "cuisines": sorted({r.cuisine for r in recipes if r.cuisine}),
        "recipes": [recipe_entry(r) for r in recipes],
    }
