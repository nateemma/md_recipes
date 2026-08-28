"""recipes.json -- see contracts/recipes-json.md.

This artifact serves both the search page and any machine reader, so it is a
public interface, not an internal cache.
"""

import json

import pytest

from src import build
from src.index import build_index


@pytest.fixture(scope="module")
def index():
    recipes, violations = build.load_corpus()
    assert violations == []
    return build_index(recipes)


REQUIRED = [
    "slug", "url", "title", "summary", "category", "cuisine",
    "tags", "authors", "servings", "total_time", "ingredients",
]


def test_envelope(index):
    from .conftest import RECIPES

    assert index["count"] == len(index["recipes"])
    assert index["count"] == len(list(RECIPES.glob("*.md")))
    from src.vocabulary import Vocabulary
    from .conftest import ROOT

    vocab = Vocabulary.load(ROOT / "data" / "vocabulary.json")
    assert len(index["categories"]) == len(vocab.categories)
    assert len(index["cuisines"]) == len(vocab.cuisines)
    assert index["categories"] == sorted(index["categories"])


def test_every_recipe_has_every_required_field(index):
    for entry in index["recipes"]:
        for field in REQUIRED:
            assert field in entry, f"{entry['slug']} missing {field}"


def test_urls_are_root_relative_and_extensionless(index):
    for entry in index["recipes"]:
        assert entry["url"] == "/" + entry["slug"]
        assert not entry["url"].endswith(".html")


def test_grouped_ingredients_are_retained(index):
    """schema.org has nowhere for group names; this does (FR-013)."""
    walnut = next(e for e in index["recipes"] if e["slug"] == "tk_WalnutSoup")
    labels = [g["label"] for g in walnut["ingredients"]]
    assert "Walnut Cream" in labels
    assert "Pear Puree" in labels


def test_ungrouped_ingredients_have_a_null_label(index):
    entry = next(e for e in index["recipes"] if e["slug"] == "BalsamicDressing")
    assert entry["ingredients"][0]["label"] is None


def test_time_bounds_present_where_parseable(index):
    definite = [e for e in index["recipes"] if e["total_time"] == "45 minutes"]
    assert definite
    for e in definite:
        assert e["time_min"] == e["time_max"] == 45


def test_unparseable_time_yields_nulls_not_zero(index):
    """A recipe with no known time must not look like an instant one."""
    for entry in index["recipes"]:
        if entry["time_min"] is None:
            assert entry["time_max"] is None


def test_ranges_keep_both_bounds(index):
    ranged = [
        e for e in index["recipes"]
        if e["time_min"] is not None and e["time_min"] != e["time_max"]
    ]
    assert ranged, "expected at least one range like '3-5 hours'"
    for e in ranged:
        assert e["time_max"] > e["time_min"]


def test_no_encoding_damage_in_the_index(index):
    """Damaged text is worse when machine-readable (FR-024)."""
    blob = json.dumps(index, ensure_ascii=False)
    for bad in ("Â½", "â€", "�"):
        assert bad not in blob


def test_instructions_and_notes_are_excluded(index):
    """Deliberate: they roughly triple the file for no in-scope query."""
    entry = index["recipes"][0]
    assert "instructions" not in entry
    assert "notes" not in entry
    assert "headnote" not in entry


def test_index_stays_small(tmp_path, index):
    path = tmp_path / "recipes.json"
    path.write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
    size = path.stat().st_size
    assert size < 500_000, f"index is {size} bytes"


def test_every_indexed_slug_has_a_page(tmp_path, index):
    out = tmp_path / "site"
    assert build.main(["--out", str(out)]) == build.EXIT_OK
    for entry in index["recipes"]:
        assert (out / entry["slug"] / "index.html").exists()


def test_ingredient_lines_carry_no_group_labels(index):
    """A label must never leak into the ingredient list as if it were one."""
    for entry in index["recipes"]:
        for group in entry["ingredients"]:
            for item in group["items"]:
                assert not item.strip().endswith(":"), f"{entry['slug']}: {item!r}"
