"""Recipe -> markdown.

TESTS ONLY. `src/build.py` must never import this module.

Constitution Principle I makes the corpus read-only to the build, so nothing in
the build path may write markdown. This exists solely because the round-trip and
normalisation fixtures (Principle VII) cannot be asserted without re-emitting.
`tests/test_build.py` asserts that build.py does not import it.
"""

from __future__ import annotations

from .model import ComponentGroup, Recipe
from .parser import DATE_FORMAT, FRONT_MATTER_KEYS


def _front_matter_value(recipe: Recipe, key: str) -> str:
    if key == "Title":
        return recipe.title
    if key == "Summary":
        return recipe.summary or ""
    if key == "Date":
        return recipe.date.strftime(DATE_FORMAT) if recipe.date else ""
    if key == "Slug":
        return recipe.slug
    if key == "Category":
        return recipe.category
    if key == "Cuisine":
        return recipe.cuisine
    if key == "Tags":
        return ", ".join(recipe.tags)
    if key == "Authors":
        return ", ".join(recipe.authors)
    if key == "Total_Time":
        return recipe.total_time_raw or ""
    if key == "Servings":
        return recipe.servings or ""
    return ""


def _emit_group(group: ComponentGroup) -> list[str]:
    """A labelled group is its label as a bare line, then a blank line, then its list."""
    out: list[str] = []
    if group.label_raw is not None:
        out.append(group.label_raw)
        out.append("")

    # Interleave prose lines back at the positions they were read from, so a file
    # that contains them still round-trips.
    prose_by_index: dict[int, list[str]] = {}
    for p in group.prose:
        prose_by_index.setdefault(p.after_index, []).append(p.text)

    for text in prose_by_index.get(-1, []):
        out.append(text)
        out.append("")

    for i, item in enumerate(group.items):
        # Ordered numbering restarts at 1 within each group. The emitter is
        # strictly sequential even where the source was not -- that is what makes
        # bf_WhiteGazpacho a normalisation fixture rather than a round-trip one.
        out.append(f"{i + 1}. {item}" if group.ordered else f"- {item}")
        for text in prose_by_index.get(i, []):
            out.append("")
            out.append(text)

    return out


def _emit_section(title: str, groups: list[ComponentGroup]) -> list[str]:
    out = [f"## {title}", ""]
    body: list[list[str]] = []
    for group in groups:
        if group.is_empty:
            continue
        body.append(_emit_group(group))
    for n, block in enumerate(body):
        if n:
            out.append("")
        out.extend(block)
    out.append("")
    return out


def emit(recipe: Recipe) -> str:
    lines: list[str] = []

    # A key is emitted even when empty, with a trailing space. Round-trip
    # equality is measured against that trailing space.
    for key in FRONT_MATTER_KEYS:
        value = _front_matter_value(recipe, key)
        lines.append(f"{key}: {value}" if value else f"{key}: ")

    lines.append("")
    lines.append(f"# {recipe.title}")
    lines.append("")

    if recipe.headnote:
        lines.extend(recipe.headnote.split("\n"))
        lines.append("")

    lines.extend(_emit_section("Ingredients", recipe.ingredients))
    lines.extend(_emit_section("Instructions", recipe.instructions))

    # '## Notes' only when it has content -- emitting an empty heading breaks
    # round-trip on roughly a quarter of the corpus.
    if recipe.has_notes:
        lines.extend(_emit_section("Notes", recipe.notes))

    # Exactly one trailing newline.
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines) + "\n"
