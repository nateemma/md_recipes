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

# Five recipes whose '# ' heading disagrees with their Title field. The grammar
# contract requires the two to be byte-identical, so one of them is wrong in each
# case -- but neither field wins uniformly, so these were confirmed individually
# rather than resolved by a rule. The value here is the agreed canonical title,
# written to BOTH the Title field and the heading.
CANONICAL_TITLES = {
    # Title kept: the family's name for it, and what the slug reflects.
    "ChickenEnchiladas": "Lori's Chicken Enchiladas",
    "FancyCrabCakes": "Fancy Crab Cakes",
    # Heading kept: the Title carried a stray full stop.
    "ClassicLasagna": "Extra Cheesy Classic Homemade Lasagna",
    # Heading kept: it is the more informative of the two.
    "Toum": "Toum (Whipped Garlic Sauce)",
    "bf_QuesoFundido": (
        "Goat Cheese Queso Fundido with Roasted Green Chile Sauce "
        "and Blue Corn Tortilla Chips"
    ),
}

# One slug that disagrees with its filename in case only.
SLUG_FIXES = {"Toum": "Toum"}

# Two files that are blank scaffolds rather than recipes -- Title "XXXX" and
# "Recipe Name", placeholder ingredients, Authors: TBD. The old site published
# both. They move to docs/ instead, where a starting point is actually useful.
TEMPLATE_FILES = {"a_template_recipe", "template_recipe"}

# A failed export: empty Title, a slug that is only the cookbook prefix, and a
# body of empty placeholders ('- ', '1. '). The recipe it was meant to be already
# exists complete as yo_ButternutSquashSoup.md, with the same tags and author.
# Nothing is lost by dropping it.
DISCARDED_FILES = {"yo_"}

# One file whose front matter carries keys the format does not define. The
# grammar has exactly one time key, `Total_Time`, so Prep_Time and Cook_Time are
# not misspellings of valid keys -- they are fields that do not exist here.
# Folding them into the correct key keeps the information: prep 15 + cook 10 = 25,
# where the recorded Total_Time of 15 minutes had simply duplicated the prep time.
CONSOLIDATED_KEYS = {
    "ChocolateChipCookies": {"Total_Time": "25 minutes"},
}

# Sources identified after the migration, replacing the `Authors: TBD` placeholder.
# `Authors` doubles as a source field in this corpus -- it already holds books,
# restaurants and sites as well as people -- because the format has no Book key
# and the cookbook is carried only by the slug prefix.
#
# Curate is Katie Button's book; the two recipes that already carried `Curate`
# are renamed so one source has one name.
AUTHOR_ASSIGNMENTS = {
    "Croquettes": "Katie Button",
    "GarlicShrimp": "Katie Button",
    "RomescoSauce": "Katie Button",            # was Curate
    "WatermelonCornnutSalad": "Katie Button",  # was Curate
    "NankingSesameChicken": "House of Nanking",
    "Salad_SmokedFishFava": "Bistronomy",
    "SugarSpicedSalmon": "Pacifica Grill",
    "Tiramisu": "Phil Price",                  # title is "(Phil's) Tiramisu"
    "Pizookie": "BJ's Restaurant",             # summary: "copycat recipe of BJ's"
    # No source anywhere in the file. Blank is honest; TBD only looked like data.
    "MangoGrapefruitSalad": "",
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


FRONT_MATTER_KEYS = [
    "Title", "Summary", "Date", "Slug", "Category",
    "Cuisine", "Tags", "Authors", "Total_Time", "Servings",
]


def rewrite_front_matter(slug: str, text: str) -> tuple[str, list[Change]]:
    """Re-emit the front matter in the contract's key order.

    Also drops keys the format does not define and restores the trailing space on
    an empty value -- `Tags: ` not `Tags:` -- which is what round-trip equality is
    measured against.
    """
    changes: list[Change] = []
    lines = text.split("\n")
    end = next((i for i, l in enumerate(lines) if l == ""), len(lines))

    values: dict[str, str] = {}
    unknown: list[str] = []
    original_order: list[str] = []
    for line in lines[:end]:
        key, sep, value = line.partition(":")
        if not sep:
            continue
        original_order.append(key)
        if key in FRONT_MATTER_KEYS:
            values[key] = value.strip()
        else:
            unknown.append(key)

    overrides = CONSOLIDATED_KEYS.get(slug, {})
    for key, value in overrides.items():
        if values.get(key) != value:
            changes.append(Change(slug, "Total_Time", values.get(key, ""), value))
            values[key] = value

    for key in unknown:
        changes.append(Change(slug, "Key removed", key, "<not in the format>"))

    known_order = [k for k in original_order if k in FRONT_MATTER_KEYS]
    if known_order != [k for k in FRONT_MATTER_KEYS if k in values]:
        changes.append(
            Change(slug, "Key order", ", ".join(known_order[:4]) + ", ...", "contract order")
        )

    rebuilt = []
    for key in FRONT_MATTER_KEYS:
        value = values.get(key, "")
        rebuilt.append(f"{key}: {value}" if value else f"{key}: ")

    # Restoring a trailing space is a change worth reporting, but not one worth
    # naming per key -- report it once per file.
    if rebuilt != lines[:end] and not changes:
        changes.append(Change(slug, "Front matter", "<trailing space>", "restored"))

    return "\n".join(rebuilt + lines[end:]), changes


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

    if slug in SLUG_FIXES:
        current = get_front_matter(text, "Slug")
        if current != SLUG_FIXES[slug]:
            text = set_front_matter(text, "Slug", SLUG_FIXES[slug])
            changes.append(Change(slug, "Slug", current or "", SLUG_FIXES[slug]))

    if slug in CANONICAL_TITLES:
        canonical = CANONICAL_TITLES[slug]
        title = get_front_matter(text, "Title")
        if title != canonical:
            text = set_front_matter(text, "Title", canonical)
            changes.append(Change(slug, "Title", title or "", canonical))
        heading = re.search(r"^# (.*)$", text, re.MULTILINE)
        if heading and heading.group(1) != canonical:
            text = re.sub(r"^# .*$", f"# {canonical}", text, count=1, flags=re.MULTILINE)
            changes.append(Change(slug, "Heading", heading.group(1), canonical))

    if slug in AUTHOR_ASSIGNMENTS:
        wanted = AUTHOR_ASSIGNMENTS[slug]
        current = get_front_matter(text, "Authors")
        if current != wanted:
            text = set_front_matter(text, "Authors", wanted)
            changes.append(Change(slug, "Authors (source)", current or "", wanted or "(blank)"))

    authors = get_front_matter(text, "Authors")
    if authors in AUTHOR_VARIANTS:
        new = AUTHOR_VARIANTS[authors]
        text = set_front_matter(text, "Authors", new)
        changes.append(Change(slug, "Authors", authors, new))

    text, fm_changes = rewrite_front_matter(slug, text)
    changes.extend(fm_changes)

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
    templates = [f for f in files if f.stem in TEMPLATE_FILES]
    discarded = [f for f in files if f.stem in DISCARDED_FILES]
    files = [
        f for f in files
        if f.stem not in TEMPLATE_FILES and f.stem not in DISCARDED_FILES
    ]
    print(
        f"{len(files)} recipes in {args.source} "
        f"({len(templates)} templates set aside, {len(discarded)} empty stub dropped)"
    )

    all_changes: list[Change] = []
    touched: set[str] = set()
    docs = args.dest.parent / "docs"
    if not args.dry_run:
        args.dest.mkdir(parents=True, exist_ok=True)
        docs.mkdir(parents=True, exist_ok=True)
        for t in templates:
            shutil.copy2(t, docs / t.name)

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

    for t in templates:
        print(f"  {t.stem:<34} {'Moved':<18} 'recipes/' -> 'docs/'")
    for d in discarded:
        print(f"  {d.stem:<34} {'Dropped':<18} 'empty export stub'")
    if templates or discarded:
        print()

    print(f"{len(all_changes)} corrections across {len(touched)} of {len(files)} files")
    if args.dry_run:
        print("\nDRY RUN -- nothing written.")
    else:
        print(f"\nWritten to {args.dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
