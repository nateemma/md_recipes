"""Validation must report, never correct (Constitution Principle III)."""

from src.vocabulary import (
    Vocabulary,
    check_encoding,
    check_slug,
    check_title_heading,
    check_trailing_newline,
)

from .conftest import ROOT

VOCAB = Vocabulary.load(ROOT / "data" / "vocabulary.json")


def test_vocabulary_shape():
    assert len(VOCAB.categories) == 15
    assert len(VOCAB.cuisines) == 13
    assert "ToTry" in VOCAB.excluded_categories


def test_good_values_produce_no_violations():
    assert VOCAB.check_category("f.md", "Dinner") == []
    assert VOCAB.check_cuisine("f.md", "French") == []
    assert VOCAB.check_authors("f.md", ["Phil Price"]) == []


def test_excluded_category_fails_and_says_why():
    (v,) = VOCAB.check_category("f.md", "ToTry")
    assert v.field == "Category" and v.value == "ToTry"
    assert "workflow state" in v.message


def test_cuisine_leak_as_category_fails():
    (v,) = VOCAB.check_category("f.md", "Mexican")
    assert "cuisine, not a category" in v.message


def test_variant_category_fails_but_names_the_correction():
    """It says 'did you mean Sauce?' -- it does not apply it."""
    (v,) = VOCAB.check_category("f.md", "Sauces")
    assert "Sauce" in v.message
    assert VOCAB.category_variants["Sauces"] == "Sauce"


def test_unknown_cuisine_fails():
    (v,) = VOCAB.check_cuisine("f.md", "Klingon")
    assert v.field == "Cuisine"


def test_misspelled_author_fails_with_canonical_form():
    (v,) = VOCAB.check_authors("f.md", ["Ottolenghi"])
    assert "Yotam Ottolenghi" in v.message


def test_second_author_misspelling_is_caught():
    """Found in research R4; the feature prompt does not list it."""
    (v,) = VOCAB.check_authors("f.md", ["Pastrey Living with Anya"])
    assert "Pastry Living with Anya" in v.message


def test_placeholder_author_is_rejected():
    """'TBD' rendered as "From TBD" and shipped as a Person named TBD."""
    (v,) = VOCAB.check_authors("f.md", ["TBD"])
    assert "placeholder" in v.message


def test_blank_authors_is_allowed():
    """The format emits every key even when empty. Saying nothing is honest;
    saying 'TBD' is not."""
    assert VOCAB.check_authors("f.md", []) == []


def test_authors_are_an_open_set():
    """No allowlist exists, so a brand-new author must pass (research R4)."""
    assert VOCAB.check_authors("f.md", ["Some New Cookbook Author"]) == []


def test_all_violations_reported_not_just_the_first():
    violations = (
        VOCAB.check_category("f.md", "ToTry")
        + VOCAB.check_cuisine("f.md", "Klingon")
        + VOCAB.check_authors("f.md", ["Ottolenghi", "Pastrey Living with Anya"])
    )
    assert len(violations) == 4


def test_slug_must_match_filename():
    assert check_slug("f.md", "Foo", "Foo") == []
    (v,) = check_slug("Bar.md", "Foo", "Bar")
    assert "filename stem" in v.message


def test_slug_charset_enforced():
    violations = check_slug("f.md", "foo-bar", "foo-bar")
    assert any("A-Za-z0-9_" in v.message for v in violations)


def test_heading_must_equal_title():
    assert check_title_heading("f.md", "T", "T") == []
    (v,) = check_title_heading("f.md", "T", "Other")
    assert v.field == "Title"


def test_encoding_damage_detected_with_line_number():
    (v,) = check_encoding("f.md", "ok\nabout 1Â½ cups\nok\n")
    assert v.line == 2 and v.field == "Encoding"


def test_clean_text_has_no_encoding_violations():
    assert check_encoding("f.md", "1½ cups of crème fraîche at 180°\n") == []


def test_trailing_newline_rules():
    assert check_trailing_newline("f.md", "x\n") == []
    assert len(check_trailing_newline("f.md", "x")) == 1
    assert len(check_trailing_newline("f.md", "x\n\n")) == 1
