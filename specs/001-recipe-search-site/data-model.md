# Phase 1: Data Model — Search-First Recipe Site

**Feature**: `001-recipe-search-site` | **Date**: 2026-08-26

One parse produces these objects. The templates, the JSON-LD and the index are all consumers of
them and nothing else (Constitution Principle IV).

---

## `Recipe`

The whole of one markdown file. Immutable once parsed.

| Field | Type | Source | Notes |
|---|---|---|---|
| `slug` | `str` | filename minus `.md` | Identity. `^[A-Za-z0-9_]+$`. MUST equal the `Slug` front-matter value (FR-006). |
| `title` | `str` | `Title:` | Required, non-empty. MUST equal the `# ` heading text byte-for-byte. |
| `summary` | `str \| None` | `Summary:` | `None` when empty — 19 corpus files. |
| `date` | `datetime \| None` | `Date:` | `YYYY-MM-DD HH:MM`, space not `T`, no timezone. |
| `category` | `str` | `Category:` | One of the 15 canonical values. Validated, never coerced. |
| `cuisine` | `str` | `Cuisine:` | One of the 13 canonical values. Validated, never coerced. |
| `tags` | `list[str]` | `Tags:` | Comma-space separated. Empty list when the value is empty — 5 corpus files. |
| `authors` | `list[str]` | `Authors:` | Plural key, usually a single value. Validated against the variant map only (R4). |
| `total_time_raw` | `str \| None` | `Total_Time:` | Free text, preserved verbatim. Never empty in the current corpus (R5). |
| `total_time` | `TimeRange \| None` | derived | `None` when unparseable — `overnight`. |
| `servings` | `str \| None` | `Servings:` | Free text: `4`, `4-6`, `8 (small) servings`. |
| `headnote` | `str \| None` | body before the first `##` | Markdown. 183 of 211 have one. May contain an italic attribution line. |
| `ingredients` | `list[ComponentGroup]` | `## Ingredients` | Always at least one group; unnamed when the recipe has no components. |
| `instructions` | `list[ComponentGroup]` | `## Instructions` | Same. Numbering restarts at 1 in each group. |
| `notes` | `list[str]` | `## Notes` | Empty list when the section is absent — 54 of 211 (FR-009). |

**Derived, not stored**: `is_grouped_ingredients` / `is_grouped_instructions` — true when any group
has a `label`. Used by templates to decide whether to render component headings, and by `jsonld.py`
to choose `HowToSection` over a flat `HowToStep` list.

### Validation rules

Applied by `vocabulary.py` before rendering. All violations across all files accumulate; the build
reports them together and exits non-zero without writing output (FR-030, FR-031).

| Rule | Failure message names |
|---|---|
| `category` ∈ the 15 canonical values | file, field, offending value, and — when the value is in `categoryVariants` or `excludedCategories` — what it should be or why it is forbidden |
| `cuisine` ∈ the 13 canonical values | file, field, offending value |
| no author is a key in `authorVariants` | file, the misspelling, and its canonical form |
| `slug` == filename stem | file, both values |
| `title` == `# ` heading text | file, both values |
| no `Â`, `â€` or `U+FFFD` anywhere in the file | file, line number, the damaged run |
| file ends with exactly one `\n` | file |

`Category: ToTry`, `Category: American` and `Category: Mexican` are in `excludedCategories` and can
never pass. That is the mechanism by which a regression of the migration fails the build.

---

## `ComponentGroup`

An optionally named part of a recipe, one level deep, never nested (FR-004). A recipe with no named
components has exactly one group whose `label` is `None`.

| Field | Type | Notes |
|---|---|---|
| `label` | `str \| None` | Display form: surrounding `**` stripped, trailing `:` stripped. `Walnut Cream:` → `Walnut Cream`. |
| `label_raw` | `str \| None` | The source line verbatim. The emitter re-emits this, so round-trip stays byte-exact. |
| `items` | `list[str]` | Ingredient or instruction lines, marker (`- ` / `1. `) removed, order preserved. |
| `prose` | `list[ProseLine]` | Lines that are neither items nor labels. Usually empty. |

`items` and `prose` both keep their source position via `ProseLine.after_index`, so a group renders
in source order rather than items-then-prose.

### How a bare line is classified

Applied in order to each non-list line inside `## Ingredients` / `## Instructions` (R3). Measured
over the corpus: 408 labels, 89 prose, 24 discarded, from 521 bare lines.

1. **Whitespace-only** → discarded. It is not empty (so the reference implementation treats it as a
   label) but it carries nothing.
2. **Ends with `:`** after stripping surrounding `**` → **label**. Closes the previous group.
3. **Next non-blank line in the section is a list item, AND length ≤ 60, AND does not end in `.`**
   → **label**. The structural test: a real label introduces a list.
4. **Otherwise** → **`ProseLine`** attached to the current group.

Every classification is written to `build/parse-report.md` for audit (Principle VI).

---

## `ProseLine`

A line inside a section that is neither a list item nor a component label — 89 across the corpus,
almost all OCR line-wrapping in the `bf_` cookbook import.

| Field | Type | Notes |
|---|---|---|
| `text` | `str` | The line, verbatim. |
| `after_index` | `int` | Index in the enclosing group's `items` that this line followed. `-1` when it precedes every item. |

Rendered as a paragraph within the group. Never a heading, never dropped, never merged into an
adjacent item — merging would guess at intent (Principle VI). Excluded from `recipeIngredient` and
from the search index's ingredient lines, because a sentence fragment is not an ingredient.

---

## `TimeRange`

Parsed from `Total_Time` free text (R5).

| Field | Type | Notes |
|---|---|---|
| `min_minutes` | `int` | Lower bound. |
| `max_minutes` | `int` | Upper bound. Equals `min_minutes` for a definite time. |
| `is_definite` | `bool` | Derived: `min_minutes == max_minutes`. |

| Source form | Result | JSON-LD `totalTime` |
|---|---|---|
| `45 minutes` | 45–45 | `PT45M` |
| `2 hours` | 120–120 | `PT2H` |
| `2 hours 30 minutes` | 150–150 | `PT2H30M` |
| `2 days` | 2880–2880 | `P2D` |
| `3-5 hours` | 180–300 | *omitted* |
| `overnight`, empty, unrecognised | `None` | *omitted* |

Emitted to JSON-LD only when `is_definite` (FR-012) — 207 of 211 recipes. The "under an hour"
filter tests `max_minutes <= 60`; a recipe with `total_time is None` is excluded from that filtered
set rather than treated as zero (FR-016).

---

## `Vocabulary`

Loaded from `data/vocabulary.json`, copied from RecipeScanner. Read-only; regenerating it is the
other project's decision (FR-042).

| Field | Type | Contents |
|---|---|---|
| `categories` | `list[str]` | The 15 canonical values. |
| `cuisines` | `list[str]` | The 13 canonical values. |
| `category_variants` | `dict[str, str]` | `Sauces`→`Sauce`, `SideS`→`Sides`. Expected to be **empty of corpus hits** after migration — used to produce a helpful error, never to coerce. |
| `cuisine_variants` | `dict[str, str]` | Currently empty. |
| `author_variants` | `dict[str, str]` | `Ottolenghi`→`Yotam Ottolenghi`, `Pastrey Living with Anya`→`Pastry Living with Anya`. |
| `excluded_categories` | `list[str]` | `ToTry`, `American`, `Mexican`. Never valid as a category. |

**There is no author allowlist** (R4). Authors are an open set — 48 distinct values today, one more
per new cookbook. Validation therefore only rejects known misspellings.

---

## `Violation`

What validation accumulates. Rendered to stderr, one per line, sorted by file.

| Field | Type |
|---|---|
| `file` | `str` — path relative to the repository root |
| `field` | `str` — `Category`, `Cuisine`, `Authors`, `Slug`, `Title`, `Encoding`, `Trailing newline` |
| `value` | `str` — the offending value |
| `message` | `str` — what is wrong and, where known, what it should be |

---

## Migration record

Not a runtime type — the output of `tools/migrate_corpus.py`, which runs once. Every change is a
reviewable diff (FR-025).

| Correction | Files | Rule |
|---|---:|---|
| `Category: ToTry` → real category | 27 | 6 `Soup`, 11 `Dinner`, 3 `Sides`, 7 `Appetizer`. Never `Tapas` (FR-026a). |
| `Category: Sauces` → `Sauce` | 2 | From `categoryVariants`. |
| `Category: SideS` → `Sides` | 1 | From `categoryVariants`. |
| `Category: American` → `Appetizer` | 1 | `bf_TunaCevichePineapple` — cuisine already `American`; category was missing. |
| `Category: Mexican` → `Dinner` | 1 | `bf_YucatanChickenWraps` — cuisine already `Southwestern`; category was missing. |
| `Authors: Ottolenghi` → `Yotam Ottolenghi` | 2 | From `authorVariants`. |
| `Authors: Pastrey Living with Anya` → `Pastry Living with Anya` | 1 | From `authorVariants`. Not listed in the feature prompt (R4). |
| Encoding repair | 3 | `cp1252` → `utf-8` round-trip. `8″`, `20–30ml`, `1½`. |
| Trailing newline | 18 | End with exactly one `\n`. |

Two of these need the user's confirmation before the migration runs, because the feature prompt
records the category as "simply missing" without saying what it should be: `bf_TunaCevichePineapple`
and `bf_YucatanChickenWraps`. The values above are proposals (Principle VI).

**Not changed**: the four remaining OCR errors in `tk_WalnutSoup.md` (content editing, out of
scope), and `Authors: TBD` on 10 recipes (surfaced in R4, awaiting a decision).
