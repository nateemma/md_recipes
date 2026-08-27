"""Recipe -> schema.org/Recipe.

See contracts/recipe-jsonld.md. The point is that a crawler or an assistant gets
the recipe without parsing the page's markup.
"""

from __future__ import annotations

from typing import Any

from .model import Recipe
from .timeparse import to_iso8601

SITE_URL = "https://recipes.nateemma.com"


def recipe_jsonld(recipe: Recipe) -> dict[str, Any]:
    data: dict[str, Any] = {
        "@context": "https://schema.org",
        "@type": "Recipe",
        "name": recipe.title,
        "url": f"{SITE_URL}/{recipe.slug}",
    }

    if recipe.summary:
        data["description"] = recipe.summary
    if recipe.date:
        data["datePublished"] = recipe.date.strftime("%Y-%m-%d")
    if recipe.category:
        data["recipeCategory"] = recipe.category
    if recipe.cuisine:
        data["recipeCuisine"] = recipe.cuisine
    if recipe.tags:
        data["keywords"] = ", ".join(recipe.tags)
    if recipe.authors:
        data["author"] = [
            {"@type": "Person", "name": name} for name in recipe.authors
        ]
    if recipe.servings:
        data["recipeYield"] = recipe.servings

    # Only a definite duration. schema.org's totalTime is a single Duration with
    # nowhere to express a range, so '3-5 hours' is omitted rather than reported
    # as a number the source never claimed.
    iso = to_iso8601(recipe.total_time)
    if iso:
        data["totalTime"] = iso

    # Flat, source order, group names dropped. Nothing in this array is anything
    # other than an ingredient -- a consumer counting items or building a
    # shopping list must not be handed 'Walnut Cream:' as an entry.
    data["recipeIngredient"] = recipe.ingredient_lines()

    data["recipeInstructions"] = _instructions(recipe)
    return data


def _instructions(recipe: Recipe) -> list[dict[str, Any]]:
    """HowToSection when grouped, a flat HowToStep list otherwise.

    schema.org *does* model instruction grouping, so grouping is kept where the
    vocabulary supports it and dropped only where it does not.
    """
    if recipe.is_grouped_instructions:
        sections: list[dict[str, Any]] = []
        for group in recipe.instructions:
            if not group.items:
                continue
            sections.append(
                {
                    "@type": "HowToSection",
                    "name": group.label or "",
                    "itemListElement": [
                        {"@type": "HowToStep", "text": item} for item in group.items
                    ],
                }
            )
        return sections
    return [
        {"@type": "HowToStep", "text": item} for item in recipe.instruction_lines()
    ]
