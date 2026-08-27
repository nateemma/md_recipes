"""The shared vocabulary, and validation against it.

Constitution Principle III: validate, never normalise. Nothing here rewrites a
value. The variant maps exist to make an error message helpful -- to say "did you
mean 'Sauce'?" -- and never to silently substitute.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from .model import Violation

DAMAGE_PATTERNS = [
    ("�", "U+FFFD replacement character"),
    ("Â", "'Â' -- UTF-8 read as cp1252"),
    ("â€", "'â€' -- UTF-8 read as cp1252"),
]

SLUG_RE = re.compile(r"^[A-Za-z0-9_]+$")

# `Authors` may legitimately be empty -- the format emits every key even when it
# has no value. What it may not be is a placeholder that looks like a source:
# 'TBD' rendered as "From TBD" on the page and shipped as a Person named TBD in
# the structured data, which is worse than saying nothing.
PLACEHOLDER_AUTHORS = {"TBD", "TODO", "UNKNOWN", "N/A", "XXX"}


@dataclass(frozen=True)
class Vocabulary:
    categories: list[str]
    cuisines: list[str]
    category_variants: dict[str, str]
    cuisine_variants: dict[str, str]
    author_variants: dict[str, str]
    excluded_categories: list[str]

    @classmethod
    def load(cls, path: str | Path) -> "Vocabulary":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(
            categories=data["categories"],
            cuisines=data["cuisines"],
            category_variants=data.get("categoryVariants", {}),
            cuisine_variants=data.get("cuisineVariants", {}),
            author_variants=data.get("authorVariants", {}),
            excluded_categories=data.get("excludedCategories", []),
        )

    # -- individual field checks -------------------------------------------------

    def check_category(self, file: str, value: str) -> list[Violation]:
        if value in self.categories:
            return []
        if value in self.excluded_categories:
            why = {
                "ToTry": "it is a workflow state, not a category",
                "American": "it is a cuisine, not a category",
                "Mexican": "it is a cuisine, not a category",
            }.get(value, "it is excluded from the vocabulary")
            msg = f"{value!r} is not a category ({why})"
        elif value in self.category_variants:
            msg = (
                f"{value!r} is not in the vocabulary "
                f"-- did you mean {self.category_variants[value]!r}?"
            )
        else:
            msg = f"{value!r} is not one of the {len(self.categories)} known categories"
        return [Violation(file, "Category", value, msg)]

    def check_cuisine(self, file: str, value: str) -> list[Violation]:
        if value in self.cuisines:
            return []
        if value in self.cuisine_variants:
            msg = (
                f"{value!r} is not in the vocabulary "
                f"-- did you mean {self.cuisine_variants[value]!r}?"
            )
        else:
            msg = f"{value!r} is not one of the {len(self.cuisines)} known cuisines"
        return [Violation(file, "Cuisine", value, msg)]

    def check_authors(self, file: str, values: list[str]) -> list[Violation]:
        """Authors are an OPEN set.

        vocabulary.json carries no author allowlist -- only a variant map (research
        R4). Categories and cuisines are closed vocabularies; authors are not, since
        every new cookbook adds one. So this rejects known misspellings and lets
        anything else through. Validating against a generated allowlist would fail
        the build on every genuinely new author, which inverts the intent of FR-030.
        """
        out: list[Violation] = []
        for value in values:
            if value.strip().upper() in PLACEHOLDER_AUTHORS:
                out.append(
                    Violation(
                        file,
                        "Authors",
                        value,
                        f"{value!r} is a placeholder, not a source "
                        "-- name the source, or leave Authors empty",
                    )
                )
                continue
            if value in self.author_variants:
                out.append(
                    Violation(
                        file,
                        "Authors",
                        value,
                        f"{value!r} is a known misspelling of "
                        f"{self.author_variants[value]!r}",
                    )
                )
        return out


# -- file-level checks that need no vocabulary ----------------------------------


def check_slug(file: str, slug: str, filename_stem: str) -> list[Violation]:
    out: list[Violation] = []
    if not SLUG_RE.match(slug):
        out.append(
            Violation(file, "Slug", slug, f"{slug!r} does not match ^[A-Za-z0-9_]+$")
        )
    if slug != filename_stem:
        out.append(
            Violation(
                file,
                "Slug",
                slug,
                f"{slug!r} does not equal the filename stem {filename_stem!r}",
            )
        )
    return out


def check_title_heading(file: str, title: str, heading: str | None) -> list[Violation]:
    if heading is None:
        return [Violation(file, "Title", title, "no '# ' heading found in the body")]
    if heading != title:
        return [
            Violation(
                file,
                "Title",
                title,
                f"the '# ' heading {heading!r} does not equal Title {title!r}",
            )
        ]
    return []


def check_not_empty(file: str, title: str, ingredients: list[str],
                    instructions: list[str]) -> list[Violation]:
    """A recipe must actually be one.

    A failed export -- empty Title, empty '- ' and '1. ' placeholders -- would
    otherwise publish as a blank page, and in a site whose only navigation is
    search it would surface in results as a recipe with no name.
    """
    out: list[Violation] = []
    if not title.strip():
        out.append(Violation(file, "Title", "", "Title is empty"))
    if not [i for i in ingredients if i.strip()]:
        out.append(Violation(file, "Ingredients", "", "no non-empty ingredient lines"))
    if not [i for i in instructions if i.strip()]:
        out.append(Violation(file, "Instructions", "", "no non-empty instruction lines"))
    return out


def check_encoding(file: str, text: str) -> list[Violation]:
    """Damaged text is a validation failure, not a warning.

    Publishing mojibake as machine-readable data is worse than publishing it on a
    page, so the build refuses rather than passing it into JSON-LD or the index.
    """
    out: list[Violation] = []
    for lineno, line in enumerate(text.split("\n"), start=1):
        for pattern, description in DAMAGE_PATTERNS:
            if pattern in line:
                idx = line.index(pattern)
                excerpt = line[max(0, idx - 8) : idx + 12]
                out.append(
                    Violation(
                        file,
                        "Encoding",
                        excerpt,
                        f"damaged text {excerpt!r} -- {description}",
                        line=lineno,
                    )
                )
                break
    return out


def check_front_matter_keys(file: str, text: str, expected: list[str]) -> list[Violation]:
    """The front matter has exact keys in an exact order (Principle II).

    A key the format does not define is rejected rather than ignored: the format
    belongs to RecipeScanner, whose emitter would silently drop such a key on any
    round-trip, so tolerating it here would let the corpus grow a second format
    that only one of the two projects can read.
    """
    out: list[Violation] = []
    found: list[str] = []
    for line in text.split("\n"):
        if line == "":
            break
        key, sep, _ = line.partition(":")
        if not sep:
            continue
        found.append(key)
        if key not in expected:
            out.append(
                Violation(
                    file,
                    "Front matter",
                    key,
                    f"{key!r} is not a key in this format "
                    f"(the format defines exactly: {', '.join(expected)})",
                )
            )

    known = [k for k in found if k in expected]
    if known != [k for k in expected if k in known]:
        out.append(
            Violation(
                file,
                "Front matter",
                ", ".join(known),
                "keys are not in the order the format defines",
            )
        )
    return out


def check_trailing_newline(file: str, text: str) -> list[Violation]:
    if not text.endswith("\n"):
        return [
            Violation(file, "Trailing newline", "", "file does not end with a newline")
        ]
    if text.endswith("\n\n"):
        return [
            Violation(
                file,
                "Trailing newline",
                "",
                "file ends with more than one newline",
            )
        ]
    return []
