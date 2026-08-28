"""The recipe template in docs/ must actually build.

It is what someone copies to add a recipe, so a template that fails validation
is worse than no template -- it teaches the wrong shape.
"""

import shutil

from src import build
from src.parser import FRONT_MATTER_KEYS, parse_file

from .conftest import ROOT

TEMPLATE = ROOT / "docs" / "recipe-template.md"


def test_template_exists():
    assert TEMPLATE.exists()


def test_template_has_the_ten_keys_in_order():
    keys = []
    for line in TEMPLATE.read_text(encoding="utf-8").split("\n"):
        if line == "":
            break
        key, sep, _ = line.partition(":")
        if sep:
            keys.append(key)
    assert keys == FRONT_MATTER_KEYS


def test_template_keeps_the_trailing_space_on_empty_keys():
    for line in TEMPLATE.read_text(encoding="utf-8").split("\n"):
        if line == "":
            break
        key, sep, value = line.partition(":")
        if sep and value.strip() == "":
            assert value == " ", f"{key!r} lost its trailing space"


def test_template_does_not_use_a_placeholder_author():
    """Both previous templates said `Authors: TBD`, which now fails the build."""
    assert "TBD" not in TEMPLATE.read_text(encoding="utf-8")


def test_dropping_the_template_into_the_corpus_builds(tmp_path):
    """The whole claim of docs/adding-a-recipe.md, checked end to end."""
    corpus = tmp_path / "recipes"
    corpus.mkdir()
    for src in (ROOT / "recipes").glob("*.md"):
        shutil.copy2(src, corpus / src.name)

    text = TEMPLATE.read_text(encoding="utf-8")
    text = text.replace("Recipe Name", "Brand New Dish").replace(
        "Slug: RecipeName", "Slug: BrandNewDish"
    )
    (corpus / "BrandNewDish.md").write_text(text, encoding="utf-8")

    out = tmp_path / "site"
    assert build.main(["--out", str(out), "--corpus", str(corpus)]) == build.EXIT_OK
    assert (out / "BrandNewDish" / "index.html").exists()

    recipe = parse_file(corpus / "BrandNewDish.md")
    assert recipe.title == "Brand New Dish"
    assert recipe.authors == []  # blank is legitimate
