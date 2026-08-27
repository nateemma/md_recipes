"""The three-way fixture split (Constitution Principle VII).

A parser that round-trips the dirty files perfectly is failing, not passing.
Correct behaviour is defined by which set a file belongs to:

  RoundTrip/     parse -> emit is byte-identical
  Normalisation/ parse -> emit produces a specific CORRECTED form
  Damage/        real published OCR errors survive untouched

The fixture files themselves are byte-identical copies from RecipeScanner and
must not be edited here. `expected/` holds this project's assertion about what
each Normalisation fixture emits -- see its README for why Succotash.md is
unchanged here but changes in RecipeScanner.
"""

import pytest

from src.emitter import emit
from src.parser import parse_file

from .conftest import FIXTURES

ROUNDTRIP = sorted((FIXTURES / "RoundTrip").glob("*.md"))
NORMALISATION = sorted((FIXTURES / "Normalisation").glob("*.md"))
DAMAGE = sorted((FIXTURES / "Damage").glob("*.md"))

# The five published OCR errors in tk_WalnutSoup.md. These are real, they are
# live on the site, and the fixture must keep all five however the published
# file is later corrected.
WALNUT_SOUP_ERRORS = ["& wedges", "1 1/s cups", "1 ltbsp", "1Â½", "toosted"]


def test_all_three_fixture_sets_are_present():
    assert len(ROUNDTRIP) == 5
    assert len(NORMALISATION) == 5
    assert len(DAMAGE) == 3


@pytest.mark.parametrize("path", ROUNDTRIP, ids=lambda p: p.name)
def test_roundtrip_is_byte_identical(path):
    source = path.read_text(encoding="utf-8")
    assert emit(parse_file(path)) == source


@pytest.mark.parametrize("path", NORMALISATION, ids=lambda p: p.name)
def test_normalisation_emits_the_specific_corrected_form(path):
    expected = (FIXTURES / "expected" / path.name).read_text(encoding="utf-8")
    assert emit(parse_file(path)) == expected


@pytest.mark.parametrize(
    "name,marker",
    [
        ("BroccoliSalad.md", "gains a trailing newline"),
        ("GreekHarissa.md", "collapses blank lines between ordered items"),
        ("SpaghettiBolognese.md", "renumbers a sequence that skips 12."),
        ("bf_WhiteGazpacho.md", "renumbers two items both marked 1."),
    ],
)
def test_format_defect_fixtures_must_actually_change(name, marker):
    """A byte-identical result here is a FAILURE, not a pass."""
    path = FIXTURES / "Normalisation" / name
    assert emit(parse_file(path)) != path.read_text(encoding="utf-8"), (
        f"{name} round-tripped unchanged but should have been corrected: {marker}"
    )


def test_succotash_is_unchanged_because_its_defect_is_vocabulary_not_format():
    """Constitution Principle III: validate, never normalise.

    Succotash.md carries `Category: SideS`. RecipeScanner's parser maps that
    variant at read time so its emitter rewrites the file. This project must not:
    a vocabulary defect is fixed once in migration and thereafter fails the
    build. So this fixture correctly emits unchanged here.
    """
    path = FIXTURES / "Normalisation" / "Succotash.md"
    assert emit(parse_file(path)) == path.read_text(encoding="utf-8")
    assert parse_file(path).category == "SideS"  # read verbatim, never coerced


def test_white_gazpacho_numbering_is_corrected_to_sequential():
    r = parse_file(FIXTURES / "Normalisation" / "bf_WhiteGazpacho.md")
    out = emit(r)
    instructions = out.split("## Instructions")[1]
    assert "\n1. " in instructions
    assert "\n2. " in instructions
    assert "\n3. " in instructions


def test_white_gazpacho_continuation_line_is_prose_not_a_heading():
    """The documented quirk: an unmarked continuation paragraph mid-list."""
    r = parse_file(FIXTURES / "Normalisation" / "bf_WhiteGazpacho.md")
    prose = [p.text for g in r.instructions for p in g.prose]
    assert any(t.startswith("Add the bread") for t in prose)
    assert not any(
        (g.label or "").startswith("Add the bread") for g in r.instructions
    )


def test_broccoli_salad_gains_exactly_one_trailing_newline():
    path = FIXTURES / "Normalisation" / "BroccoliSalad.md"
    assert not path.read_text(encoding="utf-8").endswith("\n")
    out = emit(parse_file(path))
    assert out.endswith("\n") and not out.endswith("\n\n")


@pytest.mark.parametrize("error", WALNUT_SOUP_ERRORS)
def test_damage_fixture_preserves_published_ocr_errors(error):
    """All five survive -- including the encoding damage, which the PUBLISHED
    file has repaired. The fixture is a committed copy and does not follow it."""
    out = emit(parse_file(FIXTURES / "Damage" / "tk_WalnutSoup.md"))
    assert error in out


@pytest.mark.parametrize("path", DAMAGE, ids=lambda p: p.name)
def test_damage_fixtures_parse_without_repair(path):
    source = path.read_text(encoding="utf-8")
    out = emit(parse_file(path))
    for marker in ("Â", "â€"):
        if marker in source:
            assert marker in out, f"{path.name}: repaired {marker!r} but must not"


def test_ordered_notes_are_not_dropped():
    """BasqueCheesecake.md numbers its notes '1. 2. 3.' rather than bulleting them.

    The reference rule accepts only '- ' in Notes, which silently discarded all
    nine -- including the line carrying this fixture's encoding damage. 16 corpus
    recipes are affected, so Notes is parsed as groups like every other section.
    """
    r = parse_file(FIXTURES / "Damage" / "BasqueCheesecake.md")
    assert len(r.note_lines()) == 9
    assert r.notes[0].ordered
    assert "â€³" in emit(r)


def test_walnut_soup_components_survive_both_sections():
    r = parse_file(FIXTURES / "Damage" / "tk_WalnutSoup.md")
    ingredient_labels = [g.label for g in r.ingredients if g.label]
    instruction_labels = [g.label for g in r.instructions if g.label]
    assert len(ingredient_labels) >= 2
    assert len(instruction_labels) >= 2
