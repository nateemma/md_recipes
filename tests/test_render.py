"""Recipe pages: structure, groups, print, and Unicode fidelity."""

import json
import re

import pytest

from src import build

from .conftest import ROOT


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    out = tmp_path_factory.mktemp("site")
    assert build.main(["--out", str(out)]) == build.EXIT_OK
    return out


def page(site, slug):
    return (site / slug / "index.html").read_text(encoding="utf-8")


def test_one_page_per_recipe(site):
    recipes, _ = build.load_corpus()
    pages = [p for p in site.iterdir() if p.is_dir() and p.name != "static"]
    assert len(pages) == len(recipes)
    for r in recipes:
        assert (site / r.slug / "index.html").exists()


def test_clean_urls_have_no_extension(site):
    """GitHub Pages serves index.html for a directory (FR-038)."""
    assert (site / "BalsamicDressing" / "index.html").exists()
    assert not (site / "BalsamicDressing.html").exists()


def test_grouped_ingredients_render_as_headings(site):
    html = page(site, "tk_WalnutSoup")
    section = html[html.index('class="ingredients"') : html.index('class="instructions"')]
    for label in ["Walnut Cream", "Pear Puree", "Poaching Liquid"]:
        assert f"<h3>{label}</h3>" in section


def test_instruction_numbering_restarts_within_each_group(site):
    html = page(site, "tk_WalnutSoup")
    section = html[html.index('class="instructions"') :]
    groups = re.findall(r"<h3>(.*?)</h3>\s*<ol>(.*?)</ol>", section, re.S)
    assert len(groups) >= 2
    for _, body in groups:
        # Each group opens a fresh <ol>, so the browser numbers it from 1.
        assert "<li>" in body


def test_ungrouped_recipe_has_no_empty_group_heading(site):
    html = page(site, "BalsamicDressing")
    section = html[html.index('class="ingredients"') : html.index('class="instructions"')]
    assert "<h3>" not in section


def test_recipe_without_notes_renders_no_notes_heading(site):
    """54 of the corpus have no Notes section."""
    html = page(site, "ApricotUpsideDownCake")
    assert "<h2>Notes</h2>" not in html


def test_recipe_with_notes_renders_them(site):
    assert "<h2>Notes</h2>" in page(site, "AnchoHoneySalmon")


def test_ordered_notes_survive_to_the_page(site):
    """BasqueCheesecake numbers its notes; the reference rule dropped all nine."""
    html = page(site, "BasqueCheesecake")
    notes = html[html.index('class="notes"') :]
    assert notes.count("<li>") >= 9


def test_headnote_and_italic_attribution_survive(site):
    html = page(site, "bf_WhiteGazpacho")
    assert 'class="headnote"' in html
    assert "<em>" in html[html.index('class="headnote"') : html.index("</article>")]


def test_prose_line_is_a_paragraph_not_a_heading(site):
    """The correction that matters most on the page."""
    html = page(site, "bf_WhiteGazpacho")
    assert "Add the bread" in html
    assert "<h3>Add the bread" not in html
    assert 'class="note-line"' in html


@pytest.mark.parametrize(
    "slug,needle",
    [
        ("bf_WhiteGazpacho", "¾"),
        ("tk_WalnutSoup", "½"),
        ("bf_CornPancakesSalmon", "Crème Fraîche"),
    ],
)
def test_unicode_survives_to_the_page(site, slug, needle):
    assert needle in page(site, slug)


def test_no_encoding_damage_anywhere_in_the_output(site):
    for path in site.rglob("*.html"):
        text = path.read_text(encoding="utf-8")
        for bad in ("Â½", "â€", "�"):
            assert bad not in text, f"{path.name} contains {bad!r}"


def test_print_stylesheet_hides_site_chrome():
    css = (ROOT / "static" / "css" / "site.css").read_text(encoding="utf-8")
    block = css[css.index("@media print") :]
    for selector in [".site-header", ".site-footer", ".search"]:
        assert selector in block


def test_title_is_html_escaped_not_raw(site):
    """A title with '&' must not break the document."""
    recipes, _ = build.load_corpus()
    amp = [r for r in recipes if "&" in r.title]
    if amp:
        html = page(site, amp[0].slug)
        assert "&amp;" in html


def test_static_assets_copied(site):
    assert (site / "static" / "css" / "site.css").exists()
    assert (site / "static" / "js" / "search.js").exists()


def test_cname_and_nojekyll_written(site):
    assert (site / "CNAME").read_text(encoding="utf-8").strip() == "recipes.nateemma.com"
    assert (site / ".nojekyll").exists()


def test_parse_report_written(site):
    report = (site / "parse-report.md").read_text(encoding="utf-8")
    assert "component labels" in report
    assert "prose lines" in report


def test_search_card_shows_the_author(site):
    html = (site / "index.html").read_text(encoding="utf-8")
    assert 'class="result-author"' in html
    assert "Bobby Flay" in html


def test_search_script_matches_against_the_author():
    """`Authors` records the source in this corpus -- people, books, restaurants
    and sites alike -- so "Ottolenghi" is a question search should answer."""
    js = (ROOT / "static" / "js" / "search.js").read_text(encoding="utf-8")
    assert "concat(r.authors" in js


def test_layout_uses_the_full_container_width():
    css = (ROOT / "static" / "css" / "site.css").read_text(encoding="utf-8")
    assert "--container: 1200px" in css
    assert "max-width: var(--container)" in css


def test_results_are_a_card_grid_so_long_titles_wrap():
    """A long title must wrap inside its own card rather than pushing the
    cuisine/course tags onto another line."""
    css = (ROOT / "static" / "css" / "site.css").read_text(encoding="utf-8")
    grid = css[css.index(".results {") :]
    assert "grid-template-columns" in grid
    assert "overflow-wrap: anywhere" in css


def test_recipe_width_is_orientation_aware():
    """Landscape keeps the 800px reading column; portrait uses nearly the whole
    screen, because on a tablet held upright that column wastes most of it.

    Measured in Chrome: iPad Pro portrait 78% -> 97% of viewport, the same
    device in landscape unchanged at 800px.
    """
    css = (ROOT / "static" / "css" / "site.css").read_text(encoding="utf-8")
    assert "@media (orientation: portrait)" in css
    block = css[css.index("@media (orientation: portrait)") :]
    block = block[: block.index("}\n}") + 3]
    assert ".recipe" in block
    assert "max-width: none" in block


def test_portrait_rule_does_not_disturb_print():
    """The print block must still win: it comes after the orientation rule."""
    css = (ROOT / "static" / "css" / "site.css").read_text(encoding="utf-8")
    assert css.index("@media (orientation: portrait)") < css.index("@media print")


def test_hero_image_is_behind_the_welcome_and_search_only(site):
    """The photo sits behind the welcome text and the search box, and stops
    above the first row of cards."""
    html = (site / "index.html").read_text(encoding="utf-8")
    hero = html[html.index('class="hero"') : html.index('class="result-count"')]
    assert 'class="welcome"' in hero
    assert 'class="search"' in hero
    assert 'class="results"' not in hero


def test_hero_image_is_shipped_and_optimised(site):
    img = site / "static" / "img" / "books.jpg"
    assert img.exists()
    size = img.stat().st_size
    assert size < 500_000, f"hero image is {size} bytes; it should be optimised"


def test_hero_image_carries_no_camera_metadata(site):
    """It is a phone photo on a public site: no EXIF, no device, no timestamps."""
    data = (site / "static" / "img" / "books.jpg").read_bytes()
    assert b"Exif" not in data
    assert b"iPhone" not in data
    assert b"http://ns.adobe.com" not in data  # XMP


def test_hero_is_faded_and_does_not_print():
    css = (ROOT / "static" / "css" / "site.css").read_text(encoding="utf-8")
    assert "books.jpg" in css
    assert "mask-image" in css          # fades out at the bottom edge
    assert ".hero::before" in css[css.index("@media print") :]  # not printed


def test_recipe_pages_have_no_hero(site):
    """The photo belongs to the search page only."""
    assert "books.jpg" not in (site / "tk_WalnutSoup" / "index.html").read_text(
        encoding="utf-8"
    )


def test_footer_does_not_carry_a_recipe_count(site):
    """It was accurate but read as a claim that would need revisiting; the
    result count above the cards already reports the live number."""
    html = (site / "index.html").read_text(encoding="utf-8")
    footer = html[html.index('class="site-footer"') :]
    assert "recipes we actually cook" in footer
    assert not re.search(r"\d+ recipes", footer)


def test_welcome_sits_on_a_translucent_card():
    """The photo shows through, but the text sits on an even ground."""
    css = (ROOT / "static" / "css" / "site.css").read_text(encoding="utf-8")
    block = css[css.index(".welcome {") : css.index(".welcome h1")]
    assert "rgba(255, 255, 255, .5)" in block
    assert "backdrop-filter: blur" in block


def test_assets_are_fingerprinted(site):
    """GitHub Pages serves everything with max-age=600, which we do not control.
    Without a content hash in the URL, a returning reader can get new HTML and a
    ten-minute-old stylesheet -- new markup meeting old styles."""
    import re

    html = (site / "index.html").read_text(encoding="utf-8")
    assert re.search(r"site\.css\?v=[0-9a-f]{10}", html)
    assert re.search(r"search\.js\?v=[0-9a-f]{10}", html)
    recipe = (site / "tk_WalnutSoup" / "index.html").read_text(encoding="utf-8")
    assert re.search(r"site\.css\?v=[0-9a-f]{10}", recipe)


def test_fingerprint_follows_the_content(tmp_path):
    from src.render import asset_version

    a = tmp_path / "a.css"
    a.write_text("body{}", encoding="utf-8")
    first = asset_version(a)
    a.write_text("body{color:red}", encoding="utf-8")
    assert asset_version(a) != first
    assert len(first) == 10
