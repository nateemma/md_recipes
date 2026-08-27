"""Invariants over all 211 published recipes.

These are the corpus's contract with itself. They are what keeps it clean as it
grows (Constitution Principle III) -- a new recipe that breaks one of them fails
here and in the build, rather than being quietly accepted.
"""

import re

import pytest

from src.build import load_corpus
from src.parser import parse_file
from src.vocabulary import Vocabulary, check_encoding, check_trailing_newline

from .conftest import RECIPES, ROOT

FILES = sorted(RECIPES.glob("*.md"))
VOCAB = Vocabulary.load(ROOT / "data" / "vocabulary.json")

EXPECTED_COUNT = 209  # 211 source files, less two blank templates moved to docs/
EXPECTED_CATEGORIES = 15
EXPECTED_CUISINES = 13


def test_corpus_size():
    assert len(FILES) == EXPECTED_COUNT


def test_corpus_has_no_violations_at_all():
    """The whole point: a clean corpus builds, a dirty one does not."""
    recipes, violations = load_corpus()
    assert violations == []
    assert len(recipes) == EXPECTED_COUNT


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.stem)
def test_slug_equals_filename(path):
    assert parse_file(path).slug == path.stem


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.stem)
def test_heading_equals_title(path):
    r = parse_file(path)
    assert r.heading_text == r.title


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.stem)
def test_category_and_cuisine_are_canonical(path):
    r = parse_file(path)
    assert r.category in VOCAB.categories
    assert r.cuisine in VOCAB.cuisines


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.stem)
def test_no_author_is_a_known_misspelling(path):
    assert VOCAB.check_authors(path.name, parse_file(path).authors) == []


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.stem)
def test_no_encoding_damage(path):
    assert check_encoding(path.name, path.read_text(encoding="utf-8")) == []


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.stem)
def test_exactly_one_trailing_newline(path):
    assert check_trailing_newline(path.name, path.read_text(encoding="utf-8")) == []


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.stem)
def test_every_recipe_has_ingredients_and_instructions(path):
    r = parse_file(path)
    assert r.ingredient_lines(), f"{path.stem} has no ingredients"
    assert r.instruction_lines(), f"{path.stem} has no instructions"


def test_distinct_category_count_is_unchanged_by_migration():
    """RecipeScanner's extractor asserts 15 categories and fails loudly otherwise.

    Assigning the 27 ToTry recipes from the existing 15 keeps that true;
    inventing a new category would break its build.
    """
    categories = {parse_file(p).category for p in FILES}
    assert len(categories) == EXPECTED_CATEGORIES


def test_distinct_cuisine_count_is_unchanged():
    assert len({parse_file(p).cuisine for p in FILES}) == EXPECTED_CUISINES


def test_no_workflow_state_survives_as_a_category():
    categories = {parse_file(p).category for p in FILES}
    assert not categories & set(VOCAB.excluded_categories)


def test_no_variant_spelling_survives():
    categories = {parse_file(p).category for p in FILES}
    assert not categories & set(VOCAB.category_variants)


def test_tapas_keeps_its_single_recipe():
    """The seven ambiguous small plates all became Appetizer, not Tapas."""
    tapas = [p for p in FILES if parse_file(p).category == "Tapas"]
    assert len(tapas) == 1


def _front_matter_keys(path):
    """Keys in file order. Front matter runs to the first blank line."""
    keys = []
    for line in path.read_text(encoding="utf-8").split("\n"):
        if line == "":
            break
        key, sep, _ = line.partition(":")
        if sep:
            keys.append(key)
    return keys


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.stem)
def test_front_matter_keys_are_the_contract_keys_in_order(path):
    from src.parser import FRONT_MATTER_KEYS

    assert _front_matter_keys(path) == FRONT_MATTER_KEYS


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.stem)
def test_empty_front_matter_values_keep_their_trailing_space(path):
    """`Tags: ` with the trailing space is what round-trip equality is measured
    against, so an empty value must not be written as a bare `Tags:`."""
    for line in path.read_text(encoding="utf-8").split("\n"):
        if line == "":
            break
        key, sep, value = line.partition(":")
        if sep and value.strip() == "":
            assert value == " ", f"{path.stem}: {key!r} has no trailing space"


def test_unicode_is_present_and_undamaged():
    """Vulgar fractions and accents are load-bearing here, not decoration."""
    corpus = "\n".join(p.read_text(encoding="utf-8") for p in FILES)
    for char in ["½", "¾", "°", "è", "ñ"]:
        assert char in corpus, f"expected {char!r} somewhere in the corpus"
    assert "�" not in corpus


def test_fraction_slash_survives():
    """U+2044 FRACTION SLASH, not just '/'."""
    corpus = "\n".join(p.read_text(encoding="utf-8") for p in FILES)
    assert "⁄" in corpus
