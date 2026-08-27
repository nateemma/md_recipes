"""Grammar tests -- see specs/001-recipe-search-site/contracts/markdown-grammar.md."""

import pytest

from src.parser import DISCARD, LABEL, PROSE, classify_bare_line, parse

from .conftest import FIXTURES

MINIMAL = """Title: Test Recipe
Summary: 
Date: 2025-03-22 15:30
Slug: TestRecipe
Category: Dinner
Cuisine: American
Tags: 
Authors: Phil Price
Total_Time: 30 minutes
Servings: 4

# Test Recipe

## Ingredients

- 1 cup flour

## Instructions

1. Mix.
"""


def test_front_matter_keys_parsed():
    r = parse(MINIMAL, "TestRecipe.md")
    assert r.title == "Test Recipe"
    assert r.slug == "TestRecipe"
    assert r.category == "Dinner"
    assert r.cuisine == "American"
    assert r.authors == ["Phil Price"]
    assert r.servings == "4"


def test_empty_front_matter_values_become_none_or_empty():
    r = parse(MINIMAL, "TestRecipe.md")
    assert r.summary is None
    assert r.tags == []


def test_date_uses_space_not_T_and_no_timezone():
    r = parse(MINIMAL, "TestRecipe.md")
    assert r.date is not None
    assert (r.date.year, r.date.month, r.date.hour) == (2025, 3, 15)
    assert r.date.tzinfo is None


def test_heading_text_captured_for_validation():
    r = parse(MINIMAL, "TestRecipe.md")
    assert r.heading_text == "Test Recipe"


def test_missing_front_matter_raises():
    from src.parser import ParseError

    with pytest.raises(ParseError):
        parse("# Just a heading\n")


def test_headnote_is_text_before_first_section():
    text = MINIMAL.replace("# Test Recipe\n", "# Test Recipe\n\nA lovely dish.\n")
    r = parse(text, "TestRecipe.md")
    assert r.headnote == "A lovely dish."


def test_absent_notes_section_yields_empty_list():
    r = parse(MINIMAL, "TestRecipe.md")
    assert r.notes == []


def test_notes_section_parsed_when_present():
    r = parse(MINIMAL + "\n## Notes\n\n- Keep it cold.\n", "TestRecipe.md")
    assert r.note_lines() == ["Keep it cold."]
    assert r.has_notes


def test_ordered_notes_are_kept():
    """16 corpus recipes have notes that are not '- ' bullets."""
    r = parse(MINIMAL + "\n## Notes\n\n1. First.\n2. Second.\n", "TestRecipe.md")
    assert r.note_lines() == ["First.", "Second."]
    assert r.notes[0].ordered


def test_indented_bullets_are_list_items_not_bare_lines():
    r = parse(MINIMAL + "\n## Notes\n\n  - Indented.\n", "TestRecipe.md")
    assert r.note_lines() == ["Indented."]


def test_notes_can_carry_component_labels():
    """CremeBrulee.md groups its notes under 'The custard filling' etc."""
    text = MINIMAL + "\n## Notes\n\nThe custard filling:\n\n- Do not over-mix.\n"
    r = parse(text, "TestRecipe.md")
    assert [g.label for g in r.notes] == ["The custard filling"]


def test_absent_notes_means_has_notes_is_false():
    assert not parse(MINIMAL, "TestRecipe.md").has_notes


def test_ungrouped_section_is_one_unnamed_group():
    r = parse(MINIMAL, "TestRecipe.md")
    assert len(r.ingredients) == 1
    assert r.ingredients[0].label is None
    assert r.ingredients[0].items == ["1 cup flour"]
    assert not r.is_grouped_ingredients


def test_grouped_section_splits_and_strips_label():
    r = parse(
        MINIMAL.replace(
            "- 1 cup flour",
            "**Walnut Cream:**\n\n- 1/2 cup walnuts\n\nPear Puree:\n\n- 1 large pear",
        ),
        "TestRecipe.md",
    )
    assert [g.label for g in r.ingredients] == ["Walnut Cream", "Pear Puree"]
    assert r.ingredients[0].items == ["1/2 cup walnuts"]
    assert r.ingredients[1].items == ["1 large pear"]
    assert r.is_grouped_ingredients


def test_instruction_numbering_restarts_per_group():
    r = parse(
        MINIMAL.replace(
            "1. Mix.",
            "Dough:\n\n1. Mix.\n2. Rest.\n\nSauce:\n\n1. Simmer.",
        ),
        "TestRecipe.md",
    )
    assert [g.label for g in r.instructions] == ["Dough", "Sauce"]
    assert r.instructions[0].items == ["Mix.", "Rest."]
    assert r.instructions[1].items == ["Simmer."]


# -- the four-way bare-line classification (research R3) ------------------------


def test_whitespace_only_line_is_discarded():
    assert classify_bare_line("   ", ["- x"]) == DISCARD


def test_line_ending_in_colon_is_a_label():
    assert classify_bare_line("Walnut Cream:", []) == LABEL
    assert classify_bare_line("**For the lamb:**", []) == LABEL


def test_short_line_followed_by_a_list_item_is_a_label():
    assert classify_bare_line("Chocolate Terrine", ["", "- 1 cup"]) == LABEL


def test_sentence_followed_by_a_list_item_is_prose_not_a_label():
    """The correction that matters: a sentence must never become a heading."""
    line = "Remove from the oven and allow to cool."
    assert classify_bare_line(line, ["", "3. Next"]) == PROSE


def test_long_line_is_prose():
    line = "Add the bread and half a cup of water and blend until smooth and thick"
    assert classify_bare_line(line, ["", "- x"]) == PROSE


def test_line_not_followed_by_a_list_item_is_prose():
    assert classify_bare_line("MEAT", ["", "some prose"]) == PROSE


def test_prose_records_its_position_in_the_group():
    r = parse(
        MINIMAL.replace("1. Mix.", "1. Mix.\n\nKeep going until it looks right and smooth."),
        "TestRecipe.md",
    )
    prose = r.instructions[0].prose
    assert len(prose) == 1
    assert prose[0].after_index == 0


def test_grouped_fixture_keeps_components_in_both_sections():
    from src.parser import parse_file

    r = parse_file(FIXTURES / "Damage" / "tk_WalnutSoup.md")
    assert r.is_grouped_ingredients
    assert r.is_grouped_instructions
    assert len([g for g in r.ingredients if g.label]) >= 2
