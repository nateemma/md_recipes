"""The parse audit (Constitution Principle VI).

521 bare lines in the corpus had to be classified as component labels or as
prose. That is too many decisions to take silently and too many to check by
opening 209 files, so the build writes them all to one artifact that can be read
once. It is a report, not a prompt: it never blocks the build.
"""

from __future__ import annotations

from pathlib import Path

from .model import Recipe


def write_parse_report(recipes: list[Recipe], path: Path) -> None:
    labels: list[tuple[str, str, str]] = []
    prose: list[tuple[str, str, str]] = []

    for recipe in recipes:
        for section, groups in (
            ("Ingredients", recipe.ingredients),
            ("Instructions", recipe.instructions),
            ("Notes", recipe.notes),
        ):
            for group in groups:
                if group.label:
                    labels.append((recipe.slug, section, group.label))
                for p in group.prose:
                    prose.append((recipe.slug, section, p.text))

    lines: list[str] = [
        "# Parse report",
        "",
        "Every line in the corpus that is neither a list item nor a section heading, and",
        "what the parser decided it was. Read once to confirm no sentence became a",
        "heading and no genuine component label was demoted to prose.",
        "",
        "The rule, applied in order (see research.md R3):",
        "",
        "1. Whitespace-only -> discarded.",
        "2. Ends with `:` -> **component label**.",
        "3. Next non-blank line is a list item, length <= 60, does not end in `.`"
        " -> **component label**.",
        "4. Otherwise -> **prose**, rendered as a paragraph.",
        "",
        f"**{len(labels)} component labels, {len(prose)} prose lines.**",
        "",
        "## Component labels",
        "",
        "| Recipe | Section | Label |",
        "|---|---|---|",
    ]
    for slug, section, text in labels:
        lines.append(f"| `{slug}` | {section} | {_cell(text)} |")

    lines += [
        "",
        "## Prose lines",
        "",
        "Lines kept as paragraphs. Most are OCR line-wrapping in the `bf_` cookbook",
        "import -- a sentence broken mid-flow. Treating these as component labels, as a",
        "literal reading of the reference parser would, puts a heading in the middle of a",
        "method.",
        "",
        "| Recipe | Section | Line |",
        "|---|---|---|",
    ]
    for slug, section, text in prose:
        lines.append(f"| `{slug}` | {section} | {_cell(text)} |")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _cell(text: str) -> str:
    text = text.replace("|", "\\|")
    return text if len(text) <= 110 else text[:107] + "..."
