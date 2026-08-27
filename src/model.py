"""The objects one parse produces.

Constitution Principle IV: the templates, the JSON-LD and the search index are all
consumers of these and of nothing else. No consumer re-parses markdown.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class ProseLine:
    """A line inside a section that is neither a list item nor a component label.

    89 of these across the corpus, almost all OCR line-wrapping in the `bf_` import.
    Rendered as a paragraph; never a heading, never dropped, never merged into an
    adjacent item -- merging would guess at intent (Principle VI).
    """

    text: str
    after_index: int  # index in the group's items this followed; -1 if it precedes all


@dataclass
class ComponentGroup:
    """An optionally named part of a recipe. One level deep, never nested.

    Used for all three sections. `## Notes` turns out to have exactly this shape
    too -- 16 corpus recipes have notes that are ordered, indented, grouped under
    a label, or bare prose -- so it is parsed with the same code rather than as a
    flat list of bullets (which silently dropped their content).
    """

    label: str | None = None       # display form: no surrounding **, no trailing :
    label_raw: str | None = None   # the source line verbatim, so the emitter round-trips
    items: list[str] = field(default_factory=list)
    prose: list[ProseLine] = field(default_factory=list)
    ordered: bool = False          # 'N. ' items rather than '- ' bullets

    @property
    def is_empty(self) -> bool:
        return not self.items and not self.prose and self.label is None


@dataclass(frozen=True)
class TimeRange:
    """Parsed from the free-text Total_Time field."""

    min_minutes: int
    max_minutes: int

    @property
    def is_definite(self) -> bool:
        return self.min_minutes == self.max_minutes


@dataclass
class Recipe:
    """The whole of one markdown file."""

    slug: str
    title: str
    summary: str | None = None
    date: datetime | None = None
    category: str = ""
    cuisine: str = ""
    tags: list[str] = field(default_factory=list)
    authors: list[str] = field(default_factory=list)
    total_time_raw: str | None = None
    total_time: TimeRange | None = None
    servings: str | None = None
    headnote: str | None = None
    ingredients: list[ComponentGroup] = field(default_factory=list)
    instructions: list[ComponentGroup] = field(default_factory=list)
    notes: list[ComponentGroup] = field(default_factory=list)

    # Preserved so the emitter can reproduce the file byte-for-byte.
    raw_front_matter: list[tuple[str, str]] = field(default_factory=list)
    source_path: str = ""

    @property
    def is_grouped_ingredients(self) -> bool:
        return any(g.label for g in self.ingredients)

    @property
    def is_grouped_instructions(self) -> bool:
        return any(g.label for g in self.instructions)

    @property
    def url(self) -> str:
        return f"/{self.slug}"

    def ingredient_lines(self) -> list[str]:
        """Every ingredient line, flat, in source order, group names dropped.

        This is what schema.org's recipeIngredient wants (FR-013) and what the
        search index matches free text against. Prose lines are excluded: a wrapped
        sentence fragment is not an ingredient.
        """
        return [line for group in self.ingredients for line in group.items]

    def instruction_lines(self) -> list[str]:
        return [line for group in self.instructions for line in group.items]

    def note_lines(self) -> list[str]:
        return [line for group in self.notes for line in group.items]

    @property
    def has_notes(self) -> bool:
        """'## Notes' is rendered only when it has content -- 54 of 211 have none."""
        return any(g.items or g.prose for g in self.notes)


@dataclass(frozen=True)
class Violation:
    """What validation accumulates. Never a correction that gets applied."""

    file: str
    field: str
    value: str
    message: str
    line: int | None = None

    def __str__(self) -> str:
        where = f"{self.file}:{self.line}" if self.line else self.file
        return f"{where}: {self.field}: {self.message}"
