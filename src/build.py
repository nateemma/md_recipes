"""Read the corpus, validate it, parse it, render the site.

The corpus is read-only here (Constitution Principle I). Nothing in this module
or anything it imports writes to `recipes/` -- `src/emitter.py` is deliberately
not imported, and `tests/test_build.py` asserts that.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from .model import Recipe, Violation
from .parser import FRONT_MATTER_KEYS, ParseError, parse
from .vocabulary import (
    Vocabulary,
    check_encoding,
    check_front_matter_keys,
    check_slug,
    check_title_heading,
    check_trailing_newline,
)

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "recipes"
DATA = ROOT / "data"
STATIC = ROOT / "static"
TEMPLATES = ROOT / "templates"

DOMAIN = "recipes.nateemma.com"
SITE_URL = f"https://{DOMAIN}"

EXIT_OK, EXIT_VALIDATION, EXIT_PARSE, EXIT_IO = 0, 1, 2, 3


def load_corpus(corpus: Path = CORPUS) -> tuple[list[Recipe], list[Violation]]:
    """Parse every recipe and collect every violation.

    Violations accumulate rather than raising, so one run reports all of them
    (FR-031) -- fixing a corpus one error per build is miserable.
    """
    recipes: list[Recipe] = []
    violations: list[Violation] = []
    vocab = Vocabulary.load(DATA / "vocabulary.json")

    for path in sorted(corpus.glob("*.md")):
        rel = f"recipes/{path.name}"
        text = path.read_text(encoding="utf-8")

        violations.extend(check_encoding(rel, text))
        violations.extend(check_trailing_newline(rel, text))
        violations.extend(check_front_matter_keys(rel, text, FRONT_MATTER_KEYS))

        try:
            recipe = parse(text, source_path=str(path))
        except ParseError as exc:
            violations.append(Violation(rel, "Parse", "", str(exc)))
            continue

        violations.extend(check_slug(rel, recipe.slug, path.stem))
        violations.extend(check_title_heading(rel, recipe.title, recipe.heading_text))
        violations.extend(vocab.check_category(rel, recipe.category))
        violations.extend(vocab.check_cuisine(rel, recipe.cuisine))
        violations.extend(vocab.check_authors(rel, recipe.authors))

        recipes.append(recipe)

    return recipes, violations


def report_violations(violations: list[Violation]) -> None:
    """Every violation, sorted by file, one per line. Never just the first."""
    for v in sorted(violations, key=lambda v: (v.file, v.line or 0, v.field)):
        print(str(v), file=sys.stderr)
    files = len({v.file for v in violations})
    plural = "" if len(violations) == 1 else "s"
    print(
        f"\n{len(violations)} violation{plural} in {files} file"
        f"{'' if files == 1 else 's'}. No output written.",
        file=sys.stderr,
    )


def clean_output(out: Path) -> None:
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Build the recipe site.")
    ap.add_argument("--out", type=Path, default=ROOT / "build")
    ap.add_argument("--strict", action="store_true", help="treat warnings as errors")
    ap.add_argument("--no-report", action="store_true", help="skip parse-report.md")
    ap.add_argument("--corpus", type=Path, default=CORPUS)
    args = ap.parse_args(argv)

    if not args.corpus.is_dir():
        print(f"corpus not found: {args.corpus}", file=sys.stderr)
        return EXIT_IO

    recipes, violations = load_corpus(args.corpus)

    if violations:
        report_violations(violations)
        return EXIT_VALIDATION

    if not recipes:
        print("no recipes found", file=sys.stderr)
        return EXIT_PARSE

    # Nothing is written until validation has passed.
    from .render import render_site

    clean_output(args.out)
    render_site(recipes, args.out, write_report=not args.no_report)

    print(f"{len(recipes)} recipes -> {args.out}")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
