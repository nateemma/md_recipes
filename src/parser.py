"""Port of RecipeKit's MarkdownParser.swift.

Constitution Principle II: this grammar is not ours. The authority is
`markdown-output.md` in the RecipeScanner repository; the reference implementation
is `MarkdownParser.swift`. This is a port, not a reinvention.

One deliberate divergence from the reference *implementation* -- not from the
contract -- is documented at `classify_bare_line` below.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from .model import ComponentGroup, ProseLine, Recipe
from .timeparse import parse_total_time

FRONT_MATTER_KEYS = [
    "Title", "Summary", "Date", "Slug", "Category",
    "Cuisine", "Tags", "Authors", "Total_Time", "Servings",
]

DATE_FORMAT = "%Y-%m-%d %H:%M"  # a space, not 'T', and no timezone

ORDERED_ITEM = re.compile(r"(\d+)\.\s+(.*)")

# Classification of a bare line (research R3).
MAX_LABEL_LENGTH = 60


class ParseError(Exception):
    pass


# -- bare-line classification ---------------------------------------------------

DISCARD, LABEL, PROSE = "discard", "label", "prose"


def classify_bare_line(line: str, following: list[str]) -> str:
    """Decide what a non-list, non-blank line inside a section is.

    The reference implementation treats ANY bare non-list line as a component
    label. Applied to this corpus that fabricates roughly 200 false headings out
    of 521 bare lines: 24 from whitespace-only lines (a line of spaces is not
    `isEmpty` in Swift) and 92 from OCR-wrapped sentence fragments in the `bf_`
    import. On a web page each one is a visible wrong heading.

    The written contract defines a label structurally -- "its label as a bare
    line, then a blank line, then its own list" -- so that is what this
    implements. Measured over the corpus: 408 labels, 89 prose, 24 discarded.

    This emits no byte into any markdown file, so RecipeScanner's round-trip
    tests are unaffected.
    """
    stripped = line.strip()
    if not stripped:
        return DISCARD

    core = stripped.strip("*").strip()
    if core.endswith(":"):
        return LABEL

    # The structural test: a real label introduces a list.
    next_content = next((x for x in following if x.strip()), None)
    if (
        next_content is not None
        and _is_list_item(next_content)
        and len(stripped) <= MAX_LABEL_LENGTH
        and not core.endswith(".")
    ):
        return LABEL

    return PROSE


def _list_item(line: str) -> tuple[str, bool] | None:
    """Return (text, is_ordered) if this line is a list item, else None.

    Leading whitespace is tolerated: some corpus files indent their bullets
    ('  - x'), and treating those as bare lines silently dropped their content.
    """
    stripped = line.lstrip()
    if stripped.startswith("- "):
        return stripped[2:], False
    m = ORDERED_ITEM.fullmatch(stripped)
    if m:
        return m.group(2), True
    return None


def _is_list_item(line: str) -> bool:
    return _list_item(line) is not None


def _display_label(raw: str) -> str:
    """'**Walnut Cream:**' -> 'Walnut Cream'."""
    return raw.strip().strip("*").strip().rstrip(":").strip()


# -- section parsing ------------------------------------------------------------


def parse_groups(lines: list[str], default_ordered: bool = False) -> list[ComponentGroup]:
    """Split a section's lines into component groups.

    A label closes the previous group. An unlabelled group is the common case --
    137 of 211 recipes have no named components in their ingredients.

    Used for all three sections, Notes included: 16 recipes have notes that are
    ordered, indented, grouped under a label, or bare prose, and parsing Notes as
    a flat list of '- ' bullets silently discarded all of it.
    """
    groups: list[ComponentGroup] = []
    current = ComponentGroup(ordered=default_ordered)
    seen_item = False

    def flush() -> None:
        nonlocal current, seen_item
        if not current.is_empty:
            groups.append(current)
        current = ComponentGroup(ordered=default_ordered)
        seen_item = False

    for i, line in enumerate(lines):
        if not line.strip():
            continue
        item = _list_item(line)
        if item is not None:
            text, is_ordered = item
            if not seen_item:
                # The first item in a group sets its marker style.
                current.ordered = is_ordered
                seen_item = True
            current.items.append(text)
            continue

        kind = classify_bare_line(line, lines[i + 1 :])
        if kind == DISCARD:
            continue
        if kind == LABEL:
            flush()
            current.label = _display_label(line)
            current.label_raw = line
            continue
        current.prose.append(ProseLine(line.strip(), len(current.items) - 1))

    flush()
    return groups or [ComponentGroup()]


# -- the whole file -------------------------------------------------------------


def parse(text: str, source_path: str = "") -> Recipe:
    lines = text.split("\n")

    # Front matter runs to the first blank line.
    front: dict[str, str] = {}
    order: list[tuple[str, str]] = []
    i = 0
    while i < len(lines) and lines[i] != "":
        key, sep, value = lines[i].partition(":")  # first ':' only
        if sep:
            front[key] = value.strip()
            order.append((key, value.strip()))
        i += 1

    if "Title" not in front:
        raise ParseError(f"{source_path or '<text>'}: no front matter (no Title key)")

    # Body: skip blank lines, then drop the '# ' heading.
    body = lines[i:]
    while body and not body[0].strip():
        body.pop(0)
    heading: str | None = None
    if body and body[0].startswith("# "):
        heading = body.pop(0)[2:].strip()

    headnote_lines: list[str] = []
    sections: dict[str, list[str]] = {}
    current_section: str | None = None
    for line in body:
        if line.startswith("## "):
            current_section = line[3:].strip()
            sections.setdefault(current_section, [])
        elif current_section is not None:
            sections[current_section].append(line)
        else:
            headnote_lines.append(line)

    headnote = "\n".join(headnote_lines).strip() or None

    date = None
    if front.get("Date"):
        try:
            date = datetime.strptime(front["Date"], DATE_FORMAT)
        except ValueError:
            date = None

    tags = [t.strip() for t in front.get("Tags", "").split(",") if t.strip()]
    authors = [a.strip() for a in front.get("Authors", "").split(",") if a.strip()]
    raw_time = front.get("Total_Time") or None

    slug = front.get("Slug") or (Path(source_path).stem if source_path else "")

    recipe = Recipe(
        slug=slug,
        title=front.get("Title", ""),
        summary=front.get("Summary") or None,
        date=date,
        category=front.get("Category", ""),
        cuisine=front.get("Cuisine", ""),
        tags=tags,
        authors=authors,
        total_time_raw=raw_time,
        total_time=parse_total_time(raw_time),
        servings=front.get("Servings") or None,
        headnote=headnote,
        ingredients=parse_groups(sections.get("Ingredients", []), default_ordered=False),
        instructions=parse_groups(sections.get("Instructions", []), default_ordered=True),
        # '## Notes' is present only when it has content -- 54 of 211 have none.
        # Parsed as groups, not as bare bullets: see parse_groups.
        notes=(
            parse_groups(sections["Notes"], default_ordered=False)
            if "Notes" in sections
            else []
        ),
        raw_front_matter=order,
        source_path=source_path,
    )
    recipe.heading_text = heading  # type: ignore[attr-defined]
    return recipe


def parse_file(path: str | Path) -> Recipe:
    p = Path(path)
    return parse(p.read_text(encoding="utf-8"), source_path=str(p))
