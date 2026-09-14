#!/usr/bin/env python3
"""Import recipes exported by RecipeScanner into the corpus.

Copying files in by hand works, and mostly it is fine -- RecipeScanner writes
the format correctly, so validation passes. The thing it does not protect you
from is a slug that already exists: `cp` overwrites silently, and the recipe it
replaces is gone unless git has it. That has happened once already.

So this refuses to overwrite, validates before copying rather than after, and
tells you what it is going to do first.

    python tools/import_recipes.py --dry-run     # look
    python tools/import_recipes.py               # do it
"""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.build import load_corpus  # noqa: E402
from src.parser import ParseError, parse  # noqa: E402

CORPUS = ROOT / "recipes"
# Two places, because there are two habits. `incoming/` is the staging area in
# the repository; ~/Downloads is where RecipeScanner's share sheet lands.
DEFAULT_SOURCES = [ROOT / "incoming", Path("~/Downloads").expanduser()]


def looks_like_a_recipe(path: Path) -> bool:
    """Front matter with a Title and a Slug. Keeps stray markdown out."""
    try:
        head = path.read_text(encoding="utf-8")[:600]
    except (UnicodeDecodeError, OSError):
        return False
    return head.startswith("Title:") and "\nSlug:" in head


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", type=Path, action="append", dest="sources",
                    help="where to look; repeatable. Defaults to incoming/ and ~/Downloads")
    ap.add_argument("--dry-run", action="store_true", help="report, copy nothing")
    ap.add_argument("--move", action="store_true",
                    help="move rather than copy, leaving the source empty")
    ap.add_argument("--replace", action="store_true",
                    help="allow overwriting an existing slug (you will be shown which)")
    ap.add_argument("files", nargs="*", type=Path,
                    help="specific files; otherwise every recipe in --source")
    args = ap.parse_args()

    sources = args.sources or DEFAULT_SOURCES
    if args.files:
        candidates = [Path(f).expanduser() for f in args.files]
    else:
        candidates = []
        for directory in sources:
            if directory.is_dir():
                candidates += sorted(
                    p for p in directory.glob("*.md") if looks_like_a_recipe(p)
                )
    if not candidates:
        print("No recipes found in " + ", ".join(str(s) for s in sources))
        return 0

    new, clashes, unreadable = [], [], []
    for path in candidates:
        if not path.is_file():
            unreadable.append((path, "not found"))
            continue
        try:
            recipe = parse(path.read_text(encoding="utf-8"), source_path=str(path))
        except ParseError as exc:
            unreadable.append((path, str(exc)))
            continue
        if recipe.slug != path.stem:
            unreadable.append((path, f"Slug {recipe.slug!r} != filename {path.stem!r}"))
            continue
        (clashes if (CORPUS / path.name).exists() else new).append((path, recipe))

    for directory in sources:
        if not args.files:
            print(f"{directory}{'' if directory.is_dir() else '  (not found)'}")
    print()
    for path, reason in unreadable:
        print(f"  SKIP     {path.name}\n           {reason}")
    for path, recipe in clashes:
        print(f"  EXISTS   {path.name}")
        print(f"           already in the corpus as {recipe.title!r}")
    for path, recipe in new:
        print(f"  NEW      {path.name}")
        print(f"           {recipe.title}")
        print(f"           {recipe.category} / {recipe.cuisine} / "
              f"{', '.join(recipe.authors) or 'no author'}")

    to_copy = new + (clashes if args.replace else [])
    if clashes and not args.replace:
        print(f"\n{len(clashes)} file(s) would overwrite an existing recipe and were "
              "left alone. Pass --replace if that is what you want.")
    if not to_copy:
        print("\nNothing to import.")
        return 0

    # Validate against the whole corpus before touching it, so a bad file never
    # lands in recipes/ at all.
    with tempfile.TemporaryDirectory() as tmp:
        staged = Path(tmp) / "recipes"
        staged.mkdir()
        for src in CORPUS.glob("*.md"):
            shutil.copy2(src, staged / src.name)
        for path, _ in to_copy:
            shutil.copy2(path, staged / path.name)

        import src.build as build
        recipes, violations = build.load_corpus(staged)
        if violations:
            print(f"\nValidation failed -- nothing copied.\n")
            for v in violations:
                print(f"  {v}")
            return 1
        print(f"\nValidates: {len(recipes)} recipes.")

    if args.dry_run:
        print("DRY RUN -- nothing copied.")
        return 0

    for path, recipe in to_copy:
        shutil.copy2(path, CORPUS / path.name)
        if args.move:
            path.unlink()
        print(f"  {'moved' if args.move else 'imported'} {path.name}")

    print(f"\n{len(to_copy)} recipe(s) imported. Now:")
    print("  git add recipes/ && git commit && git push")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
