"""schema.org/Recipe -- see contracts/recipe-jsonld.md."""

import json
import re

import pytest

from src import build
from src.jsonld import recipe_jsonld


@pytest.fixture(scope="module")
def recipes():
    items, violations = build.load_corpus()
    assert violations == []
    return items


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    out = tmp_path_factory.mktemp("jsonld")
    assert build.main(["--out", str(out)]) == build.EXIT_OK
    return out


def extract(html):
    m = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
    assert m, "no JSON-LD on the page"
    return json.loads(m.group(1))


def test_every_page_carries_parseable_recipe_jsonld(site):
    from .conftest import RECIPES

    pages = [p for p in site.rglob("index.html") if p.parent != site]
    assert len(pages) == len(list(RECIPES.glob("*.md")))
    for path in pages:
        data = extract(path.read_text(encoding="utf-8"))
        assert data["@context"] == "https://schema.org"
        assert data["@type"] == "Recipe"
        assert data["name"]
        assert data["recipeIngredient"]
        assert data["recipeInstructions"]


def test_required_fields_present(recipes):
    for r in recipes:
        d = recipe_jsonld(r)
        assert d["name"] == r.title
        assert d["recipeCategory"] == r.category
        assert d["recipeCuisine"] == r.cuisine
        assert d["url"].startswith("https://recipes.nateemma.com/")


def test_ingredients_are_flat_with_group_names_dropped(recipes):
    walnut = next(r for r in recipes if r.slug == "tk_WalnutSoup")
    d = recipe_jsonld(walnut)
    assert isinstance(d["recipeIngredient"], list)
    assert all(isinstance(i, str) for i in d["recipeIngredient"])
    # No entry is a group label, and none is prefixed with one.
    for item in d["recipeIngredient"]:
        assert not item.strip().endswith(":")
        assert not item.startswith("Walnut Cream:")


def test_every_ingredient_line_appears_exactly_once(recipes):
    for r in recipes:
        d = recipe_jsonld(r)
        assert d["recipeIngredient"] == r.ingredient_lines()
        assert len(d["recipeIngredient"]) == sum(
            len(g.items) for g in r.ingredients
        )


def test_grouped_instructions_use_howtosection(recipes):
    walnut = next(r for r in recipes if r.slug == "tk_WalnutSoup")
    d = recipe_jsonld(walnut)
    assert d["recipeInstructions"][0]["@type"] == "HowToSection"
    names = [s["name"] for s in d["recipeInstructions"]]
    assert "Walnut Cream" in names
    for section in d["recipeInstructions"]:
        assert section["itemListElement"][0]["@type"] == "HowToStep"


def test_ungrouped_instructions_are_a_flat_step_list(recipes):
    flat = next(r for r in recipes if not r.is_grouped_instructions)
    d = recipe_jsonld(flat)
    assert all(s["@type"] == "HowToStep" for s in d["recipeInstructions"])


def test_totaltime_emitted_for_definite_durations(recipes):
    r = next(x for x in recipes if x.total_time_raw == "45 minutes")
    assert recipe_jsonld(r)["totalTime"] == "PT45M"


def test_totaltime_omitted_for_ranges_but_recipe_still_valid(recipes):
    ranged = [r for r in recipes if r.total_time and not r.total_time.is_definite]
    assert ranged, "expected at least one range like '3-5 hours'"
    for r in ranged:
        d = recipe_jsonld(r)
        assert "totalTime" not in d
        assert d["@type"] == "Recipe" and d["name"] and d["recipeIngredient"]


def test_totaltime_omitted_when_unparseable(recipes):
    unknown = [r for r in recipes if r.total_time is None]
    for r in unknown:
        assert "totalTime" not in recipe_jsonld(r)


def test_authors_are_person_objects(recipes):
    r = next(x for x in recipes if x.authors)
    assert recipe_jsonld(r)["author"][0]["@type"] == "Person"


def test_empty_summary_omits_description(recipes):
    blank = [r for r in recipes if not r.summary]
    assert blank
    for r in blank:
        assert "description" not in recipe_jsonld(r)


def test_angle_brackets_cannot_break_out_of_the_script_element(site):
    """A title containing '<' must not close the script tag early."""
    for path in site.rglob("index.html"):
        if path.parent == site:
            continue
        html = path.read_text(encoding="utf-8")
        block = re.search(
            r'<script type="application/ld\+json">(.*?)</script>', html, re.S
        )
        assert "</script" not in block.group(1)


def test_jsonld_carries_no_encoding_damage(recipes):
    for r in recipes:
        blob = json.dumps(recipe_jsonld(r), ensure_ascii=False)
        for bad in ("Â½", "â€", "�"):
            assert bad not in blob
