#!/usr/bin/env python3
"""One-time corpus migration: copy 211 recipes in, cleaning them as they move.

This is the ONLY code in the repository that writes to `recipes/`. It lives
outside `src/` deliberately -- Constitution Principle I forbids the build path
from writing to the corpus, and the separation is the enforcement.

Run with --dry-run first. Every change is intended to be read as a diff.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

SOURCE = Path("~/Documents/website/recipes-new/content/recipes").expanduser()
DEST = Path(__file__).resolve().parent.parent / "recipes"

# -- the 27 `Category: ToTry` recipes -------------------------------------------
#
# One book's import where the category was never assigned. Their cuisines are
# already correct, so only the category is missing, and the titles carry most of
# the answer. Assigned from the existing 15 categories so the vocabulary's
# category count stays at 15 -- introducing a new one would break RecipeScanner's
# extractor assertion.
#
# The seven small plates at the end were genuinely ambiguous between Appetizer
# and Tapas; the decision was to use Appetizer for all seven and leave Tapas
# holding its single existing recipe.

TOTRY_CATEGORIES = {
    # Soups and stews (6)
    "bf_ButternutSquashSoup": "Soup",
    "bf_CornSoupOkra": "Soup",
    "bf_CrabGumbo": "Soup",
    "bf_TroutCrabSoup": "Soup",
    "bf_WhiteGazpacho": "Soup",
    "bf_Cioppino": "Soup",
    # Main courses (11)
    "bf_PiriPiriChicken": "Dinner",
    "bf_HarissaShortRibs": "Dinner",
    "bf_LambShankOrzo": "Dinner",
    "bf_PhillySteakCheeseSauce": "Dinner",
    "bf_PorkChopOssoBuco": "Dinner",
    "bf_SpanishSteakFriesBlueCheese": "Dinner",
    "bf_LobsterRedCurryCoconutRice": "Dinner",
    "bf_ChickenShellfishPaella": "Dinner",
    "bf_KaleMushroomPaella": "Dinner",
    "bf_MusselsGreenChilli": "Dinner",
    "bf_PrawnsGiganteBeans": "Dinner",
    # Side dishes (3)
    "bf_AcornSquash": "Sides",
    "bf_CornParmigiana": "Sides",
    "bf_CrispyRiceSweetPotato": "Sides",
    # Small plates (7) -- the ambiguous set, all Appetizer
    "bf_QuesoFundido": "Appetizer",
    "bf_TunaTartareCrispyRice": "Appetizer",
    "bf_TequilaCuredSalmon": "Appetizer",
    "bf_ClamsTomatoBroth": "Appetizer",
    "bf_BacalaoCrepes": "Appetizer",
    "bf_CornPancakesSalmon": "Appetizer",
    "bf_RostiGoatCheeseBeets": "Appetizer",
}

# Two files whose Category field holds a cuisine name. The cuisine is already
# recorded correctly in its own field, so the category was simply never set.
MISSING_CATEGORIES = {
    "bf_TunaCevichePineapple": "Appetizer",  # Category: American, Cuisine: American
    "bf_YucatanChickenWraps": "Dinner",      # Category: Mexican, Cuisine: Southwestern
}

# Misspellings, from vocabulary.json's variant maps.
CATEGORY_VARIANTS = {"Sauces": "Sauce", "SideS": "Sides"}
AUTHOR_VARIANTS = {
    "Ottolenghi": "Yotam Ottolenghi",
    "Pastrey Living with Anya": "Pastry Living with Anya",
}

# Mojibake: UTF-8 bytes decoded as cp1252. Not Latin-1 -- 'â€“' contains U+201C,
# which is a cp1252 codepoint and a control character in Latin-1.
DAMAGE_RE = re.compile(r"(?:Â|â€)[\x80-\xff -⁯ -ÿ]*")


class Change:
    def __init__(self, slug: str, kind: str, before: str, after: str):
        self.slug, self.kind, self.before, self.after = slug, kind, before, after

    def __str__(self) -> str:
        return f"  {self.slug:<34} {self.kind:<18} {self.before!r} -> {self.after!r}"


def repair_mojibake(text: str) -> tuple[str, list[tuple[str, str]]]:
    """Repair UTF-8-read-as-cp1252 damage. Returns (text, [(before, after)])."""
    repairs: list[tuple[str, str]] = []

    def fix(match: re.Match[str]) -> str:
        damaged = match.group(0)
        try:
            mended = damaged.encode("cp1252").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            return damaged  # leave anything we cannot confidently mend
        repairs.append((damaged, mended))
        return mended

    return DAMAGE_RE.sub(fix, text), repairs


def set_front_matter(text: str, key: str, value: str) -> str:
    """Replace one front-matter value, touching nothing else in the file."""
    pattern = re.compile(rf"^{re.escape(key)}:.*$", re.MULTILINE)
    return pattern.sub(f"{key}: {value}", text, count=1)


def get_front_matter(text: str, key: str) -> str | None:
    m = re.search(rf"^{re.escape(key)}:(.*)$", text, re.MULTILINE)
    return m.group(1).strip() if m else None


def clean(slug: str, text: str) -> tuple[str, list[Change]]:
    changes: list[Change] = []

    category = get_front_matter(text, "Category")
    if category == "ToTry" and slug in TOTRY_CATEGORIES:
        new = TOTRY_CATEGORIES[slug]
        text = set_front_matter(text, "Category", new)
        changes.append(Change(slug, "Category (ToTry)", category, new))
    elif slug in MISSING_CATEGORIES and category in ("American", "Mexican"):
        new = MISSING_CATEGORIES[slug]
        text = set_front_matter(text, "Category", new)
        changes.append(Change(slug, "Category (cuisine)", category, new))
    elif category in CATEGORY_VARIANTS:
        new = CATEGORY_VARIANTS[category]
        text = set_front_matter(text, "Category", new)
        changes.append(Change(slug, "Category (variant)", category, new))

    authors = get_front_matter(text, "Authors")
    if authors in AUTHOR_VARIANTS:
        new = AUTHOR_VARIANTS[authors]
        text = set_front_matter(text, "Authors", new)
        changes.append(Change(slug, "Authors", authors, new))

    text, repairs = repair_mojibake(text)
    for before, after in repairs:
        changes.append(Change(slug, "Encoding", before, after))

    if not text.endswith("\n"):
        text += "\n"
        changes.append(Change(slug, "Trailing newline", "<none>", "\\n"))
    else:
        stripped = text.rstrip("\n") + "\n"
        if stripped != text:
            text = stripped
            changes.append(Change(slug, "Trailing newline", "<multiple>", "\\n"))

    return text, changes


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="print changes, write nothing")
    ap.add_argument("--source", type=Path, default=SOURCE)
    ap.add_argument("--dest", type=Path, default=DEST)
    args = ap.parse_args()

    if not args.source.is_dir():
        print(f"source not found: {args.source}", file=sys.stderr)
        return 1

    files = sorted(args.source.glob("*.md"))
    print(f"{len(files)} recipes in {args.source}")

    all_changes: list[Change] = []
    touched: set[str] = set()
    if not args.dry_run:
        args.dest.mkdir(parents=True, exist_ok=True)

    for path in files:
        slug = path.stem
        text = path.read_text(encoding="utf-8")
        cleaned, changes = clean(slug, text)
        all_changes.extend(changes)
        if changes:
            touched.add(slug)
        if not args.dry_run:
            (args.dest / path.name).write_text(cleaned, encoding="utf-8")

    by_kind: dict[str, list[Change]] = {}
    for c in all_changes:
        by_kind.setdefault(c.kind, []).append(c)

    print()
    for kind in sorted(by_kind):
        group = by_kind[kind]
        print(f"{kind} ({len(group)})")
        for c in group:
            print(c)
        print()

    print(f"{len(all_changes)} corrections across {len(touched)} of {len(files)} files")
    if args.dry_run:
        print("\nDRY RUN -- nothing written.")
    else:
        print(f"\nWritten to {args.dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
