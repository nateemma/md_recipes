"""Render parsed recipes to HTML.

A consumer of the parse (Constitution Principle IV) -- it never sees markdown
source, only `Recipe` objects.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import markdown as md
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup, escape

from .index import build_index
from .jsonld import recipe_jsonld
from .model import ComponentGroup, Recipe
from .report import write_parse_report

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "templates"
STATIC = ROOT / "static"

SITE_NAME = "Price Family Recipes"
DOMAIN = "recipes.nateemma.com"

WELCOME = (
    "These are the recipes we actually cook — family favourites, things worth "
    "making twice, and a few we are still working on. It is not a comprehensive "
    "index of anything. Search is the only way around: narrow by cuisine or "
    "course, or just type an ingredient you have in the fridge."
)


def _inline(text: str) -> Markup:
    """Render inline markdown in a recipe line.

    Ingredient and instruction lines carry emphasis and the occasional link --
    `Adapted from *Bobby Flay: Chapter One*` -- so they go through markdown
    rather than being escaped flat. Everything else is autoescaped by Jinja.
    """
    html = md.markdown(text, extensions=["extra"])
    if html.startswith("<p>") and html.endswith("</p>") and html.count("<p>") == 1:
        html = html[3:-4]
    return Markup(html)


def _block(text: str) -> Markup:
    return Markup(md.markdown(text, extensions=["extra"]))


def render_group(group: ComponentGroup, ordered: bool) -> Markup:
    """One group's items and prose, in source order.

    Prose lines are rendered as paragraphs at the position they were read from,
    never as headings and never merged into an adjacent item.
    """
    prose_by_index: dict[int, list[str]] = {}
    for p in group.prose:
        prose_by_index.setdefault(p.after_index, []).append(p.text)

    parts: list[str] = []
    for text in prose_by_index.get(-1, []):
        parts.append(f"<p class=\"note-line\">{_inline(text)}</p>")

    if group.items:
        tag = "ol" if ordered else "ul"
        chunks: list[str] = [f"<{tag}>"]
        for i, item in enumerate(group.items):
            chunks.append(f"<li>{_inline(item)}</li>")
            trailing = prose_by_index.get(i)
            if trailing:
                chunks.append(f"</{tag}>")
                for text in trailing:
                    chunks.append(f"<p class=\"note-line\">{_inline(text)}</p>")
                if i + 1 < len(group.items):
                    # Numbering continues across the interruption.
                    chunks.append(f"<{tag} start='{i + 2}'>" if ordered else f"<{tag}>")
                else:
                    chunks.append("")
        if not chunks[-1].startswith(f"</{tag}") and chunks[-1] != "":
            chunks.append(f"</{tag}>")
        parts.append("".join(c for c in chunks if c))

    return Markup("".join(parts))


def make_env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES)),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.globals["render_group"] = render_group
    env.globals["site_name"] = SITE_NAME
    env.globals["domain"] = DOMAIN
    return env


def render_site(recipes: list[Recipe], out: Path, write_report: bool = True) -> None:
    env = make_env()
    recipe_tpl = env.get_template("recipe.html")
    search_tpl = env.get_template("search.html")

    out.mkdir(parents=True, exist_ok=True)

    for recipe in recipes:
        jsonld = json.dumps(recipe_jsonld(recipe), ensure_ascii=False, indent=2)
        # '</script>' inside a JSON string would close the script element early.
        jsonld = jsonld.replace("<", "\\u003c").replace(">", "\\u003e")
        html = recipe_tpl.render(
            recipe=recipe,
            headnote=_block(recipe.headnote) if recipe.headnote else None,
            jsonld=Markup(jsonld),
            recipe_count=len(recipes),
        )
        directory = out / recipe.slug
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "index.html").write_text(html, encoding="utf-8")

    index = build_index(recipes)
    (out / "recipes.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8"
    )

    (out / "index.html").write_text(
        search_tpl.render(
            welcome=WELCOME,
            recipes=recipes,
            recipe_count=len(recipes),
            categories=index["categories"],
            cuisines=index["cuisines"],
        ),
        encoding="utf-8",
    )

    if (out / "static").exists():
        shutil.rmtree(out / "static")
    shutil.copytree(STATIC, out / "static")

    (out / "CNAME").write_text(f"{DOMAIN}\n", encoding="utf-8")
    (out / ".nojekyll").write_text("", encoding="utf-8")

    if write_report:
        write_parse_report(recipes, out / "parse-report.md")
