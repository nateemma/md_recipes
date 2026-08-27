# Phase 0: Research — Search-First Recipe Site

**Feature**: `001-recipe-search-site` | **Date**: 2026-08-26

All findings below were established by reading the authoritative sources and measuring the corpus
directly, not by inference. Counts are reproducible with the commands in `quickstart.md`.

---

## R1. Build the generator directly rather than keeping Pelican

**Decision**: A single-purpose Python generator. No Pelican.

**Rationale**: The plan phase was asked to treat this as a strong recommendation rather than a
settled decision, and to say so if it disagreed. It does not disagree, and the corpus measurements
strengthen the case rather than weakening it.

Once the taxonomy pages go, Pelican is used for three things — render markdown, fill a Jinja
template, copy files — and actively obstructs a fourth. That fourth is decisive: this project needs
ingredients and instructions as *structure*, and Pelican hands a template `article.content` as one
HTML blob. The existing `recipe_reader.py` already subclasses `MarkdownReader` to escape that model.
Constitution Principle IV requires one parse feeding pages, JSON-LD and the index; under Pelican the
parse is a hook inside a framework, and under a direct generator it is the centre of the program.

The measured scale supports it: 211 recipes, 1 search page, 0 images, 0 feeds, 0 pagination.

**Alternatives considered**:
- *Keep Pelican, delete the taxonomy templates.* Rejected: retains the whole framework for
  `render markdown + fill template + copy`, and keeps the reader subclass working against the grain.
- *Static site generator in another language (Hugo, Eleventy).* Rejected: the reference parser being
  ported is precise about whitespace and Unicode, and Python expresses that directly. It also adds a
  toolchain the repository does not otherwise need.
- *No templating at all, string concatenation.* Rejected: HTML escaping of recipe titles containing
  `&` and quotes is exactly the thing a template engine gets right and hand-rolling gets wrong.

**When this would be wrong**: pagination, RSS/Atom, per-author pages, drafts, or a plugin ecosystem.
None are in scope, and Principle V requires a stated reason before adding any of them.

---

## R2. Language and dependencies

**Decision**: Python 3.12 (3.11+ supported), with `jinja2` and `markdown` as the only runtime
dependencies. `pytest` for tests. No JavaScript build step, no bundler, no CSS framework.

**Rationale**: `jinja2` for HTML escaping and templating; `markdown` for the inline and block prose
that recipes genuinely contain — italic attribution lines (`Adapted from *Bobby Flay: Chapter One*`),
links in headnotes, and emphasis inside ingredient lines. Everything else — the front-matter parse,
the group parse, the index, the JSON-LD — is standard library.

Verified on this machine: `python3` is 3.12.12; neither dependency is currently installed, so the
project needs its own `requirements.txt` and virtual environment. The old site's `venv/` is Python
3.10 and is not reused.

**Alternatives considered**: `PyYAML` (rejected — the front matter is deliberately *not* YAML;
Principle II); `python-frontmatter` (rejected — it expects fences); a search library such as
Lunr or MiniSearch (see R8).

---

## R3. Component group labels — the hardest part of the parse

**Decision**: A four-way classification of every bare (non-list, non-blank) line inside
`## Ingredients` and `## Instructions`, plus a generated audit report.

This is the most significant finding of the research phase and it was **not** anticipated by the
feature prompt. The reference parser's rule is "a bare non-list line inside a section is a component
label". Applied literally to the corpus, that rule fabricates hundreds of false headings.

**Measurement**: 521 bare lines occur inside those two sections across the corpus.

| Shape | Count | Share | Example |
|---|---:|---:|---|
| A. Whitespace-only line (spaces, not empty) | 24 | 4.6% | `BoSsam.md` — trailing-space lines |
| B. Ends with a colon | 275 | 52.8% | `Walnut Cream:`, `**For the lamb:**` |
| C. Short, no terminal punctuation | 130 | 25.0% | `Chocolate Terrine`, `Assembly`, `Paella` |
| D. Long / sentence-like | 92 | 17.7% | `Add the bread and ½ cup water and blend…` |

Category A matters because the reference parser tests `line.isEmpty`, and a line of spaces is not
empty — so under the literal rule, 24 whitespace-only lines each open a new unnamed group.
Category D is OCR line-wrapping in the `bf_` cookbook import: a sentence broken mid-flow. Under the
literal rule each one becomes an `<h3>` in the middle of a method.

**The rule adopted**, applied in order to each bare line:

1. **Whitespace-only** → discard. Contributes nothing to any output.
2. **Ends with `:`** (after stripping surrounding `**` emphasis) → **group label**. Strip the bold
   markers and the trailing colon for display.
3. **Next non-blank line in the section is a list item, and the line is ≤ 60 characters and does not
   end in `.`** → **group label**. This is the structural test: a real label introduces a list.
4. **Otherwise** → **prose line** belonging to the current group. Rendered as a paragraph, never as
   a heading, never silently dropped.

**Measured result**: 408 group labels, 89 prose lines, 24 discarded. Spot-checking the 133 labels
that do not end in a colon confirms they are genuine component names — `Saffron Crepes`,
`Pomegranate-Pecan Relish`, `The Crab Cakes`, `Assemble And Bake Quiche`.

**Residual imperfection, accepted and surfaced**: roughly ten `bf_` files are OCR-damaged badly
enough that no rule recovers their intent — `bf_CornParmigiana` has an entire component whose
ingredients were captured as instruction prose. The rule never fabricates a heading from a sentence
and never drops a line, so these files render as readable prose rather than as wrong structure.

**Human-in-the-loop (Principle VI)**: the build emits `build/parse-report.md` listing every line
classified as a label and every line classified as prose, grouped by file. The 521 decisions are
auditable once, by reading one artifact, rather than by opening 211 files. This is a report, not a
prompt — it does not block the build.

**Alternatives considered**:
- *Port the reference rule literally.* Rejected: Principle II requires porting the grammar, and the
  grammar contract defines a label as "its label as a bare line, then a blank line, then its own
  list" — the structural test above is closer to that written contract than the reference
  implementation's shortcut is. The reference parser exists to serve round-trip testing, where a
  false label round-trips harmlessly; on a web page it is a visible defect.
- *Require a trailing colon, full stop.* Rejected: loses 133 genuine labels, including every
  component in `ChocolateTerrine`, `FancyCrabCakes` and `bf_BacalaoCrepes`.
- *Fix the corpus so every label ends in a colon.* Rejected: that is a content edit to 133 lines
  across dozens of files, outside this migration's stated scope, and it would break the round-trip
  fixtures.
- *Append category-D lines to the preceding list item.* Tempting — it would repair
  `In a medium saucepan, heat` + `2 tablespoons olive oil…` into one sentence — but rejected: it
  guesses, and it corrupts the cases where the bare line is genuinely a separate remark
  (`Adapted from https://…` inside `ChewyCookies`). Principle VI: do not guess silently.

---

## R4. Validating authors — the vocabulary has no author list

**Decision**: Validate authors against `authorVariants` only. A value that is a **key** in that map
fails the build and names its canonical replacement. Any other value passes.

**Rationale**: This is a correction to an assumption in the feature prompt. `vocabulary.json`
contains `categories` (15) and `cuisines` (13) as closed lists, but for authors it contains only
`authorVariants` — a two-entry correction map. **There is no author allowlist to validate against.**

That is the right shape for the data: category and cuisine are closed vocabularies, but authors are
open by nature — the corpus already holds 48 distinct values, and every new cookbook adds one.
Validating against a generated allowlist would fail the build on every genuinely new author, which
inverts the intent of FR-030.

**Corpus measurement**, and a defect the prompt did not list:

| Value | Count | Canonical |
|---|---:|---|
| `Ottolenghi` | 2 | `Yotam Ottolenghi` |
| `Pastrey Living with Anya` | 1 | `Pastry Living with Anya` |

The second is in `authorVariants` and is a real misspelling in the corpus that the feature prompt
does not mention. Migration fixes both.

**Observation, not acted on**: 10 recipes carry `Authors: TBD` — a placeholder, structurally the same
kind of defect as `Category: ToTry`. It is *not* in `authorVariants` and not in `excludedCategories`,
so it does not fail validation, and it is outside this migration's stated scope. It is recorded here
and surfaced to the user rather than silently fixed or silently ignored (Principle VI).

---

## R5. `Total_Time` — parse to a range, emit only what is certain

**Decision**: Parse free-text time into an optional `(min_minutes, max_minutes)` pair. Emit ISO 8601
`totalTime` in JSON-LD **only when `min == max`**. Store both bounds in the index; the "under an
hour" filter tests `max_minutes <= 60`.

**Rationale**: A second correction to the prompt, which says `Total_Time` is "often empty". Measured:
**it is never empty — all 211 recipes have a value.** The parser must still handle empty defensively
for future files, but empty is not the common case here; it is currently the zero case.

Observed forms and their handling:

| Form | Count | min–max | JSON-LD |
|---|---:|---|---|
| `45 minutes`, `30 minutes`, … | 195 | n–n | `PT45M` |
| `2 hours`, `1 hour`, `4 hours` | ~30 | n–n | `PT2H` |
| `2 hours 30 minutes` | 1 | 150–150 | `PT2H30M` |
| `2 days`, `8 days` | 4 | n–n | `P2D` |
| `3-5 hours`, `3-6 hours`, `6-8 hours` | 3 | min–max | omitted |
| `overnight` | 1 | none | omitted |

Ranges and `overnight` are omitted from JSON-LD because `schema.org`'s `totalTime` is a single
`Duration` with nowhere to express uncertainty; asserting the midpoint or an endpoint would publish a
number the source does not claim. 207 of 211 recipes get a `totalTime`; 4 do not, and remain valid
Recipes (FR-012).

For search, a range keeps both bounds and `max` drives the filter, so `3-5 hours` correctly fails
"under an hour" while a hypothetical `45-50 minutes` would pass. Recipes with no parseable time are
excluded from the filtered set rather than treated as zero (FR-016).

---

## R6. Repairing the encoding damage

**Decision**: Repair the three damaged files by `text.encode('cp1252').decode('utf-8')` applied to
the damaged runs. Verified against all three.

**Rationale**: The damage is classic mojibake — UTF-8 bytes decoded as a single-byte codepage. The
codepage is **cp1252, not Latin-1**: `SpaghettiPuttanesca` contains `â€“`, whose third character is
`“` (U+201C), which exists at 0x93 in cp1252 and is a control character in Latin-1.

The complete damage, located by scanning for `Â`, `â€` and `U+FFFD`:

| File | Line | Damaged | Intended |
|---|---:|---|---|
| `BasqueCheesecake.md` | 44 | `20cm/8â€³`, `2.5â€³` | `8″`, `2.5″` (U+2033 double prime) |
| `SpaghettiPuttanesca.md` | 22 | `20â€“30ml` | `20–30ml` (U+2013 en dash) |
| `tk_WalnutSoup.md` | 47 | `1Â½ cups` | `1½ cups` (U+00BD) |

These are exactly the three files the RecipeScanner `Damage/` fixture set holds, which confirms the
scan is complete rather than merely plausible.

**Scope boundary**: `tk_WalnutSoup.md` carries five published OCR errors, of which `1Â½` is one. Only
that one is encoding damage and therefore in scope. The other four — `& wedges` for `8`, `1 1/s cups`,
`1 ltbsp sugar`, `walnuts, toosted` — are content editing and stay. The `Damage/` fixture is a
committed copy in the other repository and keeps all five regardless.

**Alternatives considered**: `ftfy` (rejected — a dependency for a one-time three-file fix, against
Principle V); hand-editing (rejected — a scripted repair with a printed before/after is reviewable
and repeatable, hand-editing is neither).

---

## R7. The index: one file, all of it, uncompressed

**Decision**: One `recipes.json` at the site root containing every recipe's structured fields and
its ingredient lines, loaded whole on page open. Estimated 250–400 KB uncompressed, well under
100 KB over the wire after the server's gzip.

**Rationale**: 211 recipes. Ingredient lines are the bulk; instructions roughly triple the size for
a search benefit the spec does not require (FR-015 scopes free text to title and ingredients).

Field selection, per FR-022 plus what search needs:

- **Included**: `slug`, `title`, `category`, `cuisine`, `tags`, `authors`, `servings`,
  `total_time` (source text), `time_min` / `time_max` (parsed minutes), `ingredients` (grouped, as
  in the parse), `summary`.
- **Excluded**: instructions, notes, headnote. Instructions roughly triple the file for no
  in-scope query; a later decision to include them is additive and breaks nothing.

The index doubles as the agent-facing whole-corpus artifact (FR-023), which is why it keeps the
grouped ingredient form and the raw `total_time` string alongside the parsed bounds — a machine
reader should not have to reverse the site's parsing decisions.

**Alternatives considered**: a prebuilt inverted index (rejected — 211 records is far below the
size where that pays); splitting into a search index plus a separate data file (rejected —
FR-023 explicitly wants one artifact serving both); compressing to a custom format (rejected —
defeats the "an agent would want this" purpose).

---

## R8. Search runs on plain JavaScript, no library

**Decision**: One `search.js`, no dependencies, no build step. Linear scan with pre-normalised
match keys.

**Rationale**: The whole corpus is one array of 211 objects. A filter pass over 211 records testing
a lowercase, accent-folded substring is sub-millisecond — orders of magnitude inside SC-004's 100 ms
budget. A search library would add a bundle, a build step and an index format to save nothing.

Accent folding (FR-021) uses `String.prototype.normalize('NFD')` with combining marks stripped, so
`creme fraiche` finds `crème fraîche` and `jalapeno` finds `jalapeño`. Match keys are computed once
at load, not per keystroke. Input is debounced only enough to avoid redundant renders.

**Alternatives considered**: MiniSearch / Lunr / Fuse (rejected — see above); Stork (explicitly
removed by the spec, FR-032); server-side search (rejected — FR-018 forbids a query backend).

---

## R9. Search state in the URL

**Decision**: Query string — `?q=anchovies&cuisine=French&category=Dinner&time=60` — written with
`history.replaceState` while typing and `history.pushState` on a filter change, and read on load.

**Rationale**: Settled by clarification. The query string is shareable and readable, and survives
being pasted into a message, which the fragment also does but less legibly. `replaceState` while
typing keeps the back button from stepping through every keystroke; `pushState` on a discrete filter
change makes back mean "undo that filter", which is what a reader expects.

An unrecognised value for `cuisine`, `category` or `time` is ignored and the corpus shown unfiltered
(FR-040), so a stale shared link degrades to the home page rather than to an empty result set.

---

## R10. URL shape and Pages behaviour

**Decision**: Write each recipe to `build/<Slug>/index.html`, served as `recipes.nateemma.com/<Slug>`.
Add `.nojekyll` and `CNAME` at the site root.

**Rationale**: GitHub Pages serves `index.html` for a directory, so the `.html` suffix the old S3
REST endpoint forced is no longer needed (FR-038). `.nojekyll` stops Jekyll from processing the
output — cheap insurance whose absence is diagnosed slowly. `CNAME` in the published artifact keeps
the custom domain across deploys, which is otherwise a recurring manual step in Pages settings.

Slugs are `^[A-Za-z0-9_]+$` per the grammar contract, so no slug needs URL escaping and no slug
collides with a reserved path.

---

## R11. Deployment

**Decision**: One workflow on push to the default branch: checkout → set up Python → install
requirements → build → `actions/upload-pages-artifact` → `actions/deploy-pages`. Permissions
`pages: write` and `id-token: write`, concurrency group `pages`.

**Rationale**: This is the whole of it. Because the build validates and exits non-zero on a
vocabulary violation (FR-030), a bad push fails the workflow before the deploy step and the live
site is untouched (FR-036) — no extra guard needed. HTTPS and certificate renewal are Pages'
responsibility (FR-037).

Two manual, one-time steps sit outside the repository and must be handed to the user rather than
attempted: pointing a `CNAME` DNS record for `recipes.nateemma.com` at `<username>.github.io`, and
entering the domain in the repository's Pages settings.

---

## R12. Testing strategy

**Decision**: `pytest`, with three layers.

1. **Fixture tests** — the three sets copied from RecipeScanner (Principle VII):
   - `RoundTrip/` (5 files): parse → emit → byte-identical.
   - `Normalisation/` (5 files): parse → emit → a specific corrected form. Includes
     `bf_WhiteGazpacho` (duplicate `1.` numbering) and `BroccoliSalad` (missing trailing newline).
   - `Damage/` (3 files): the five published OCR errors survive parsing untouched.

   A parser that round-trips a `Normalisation/` file unchanged is failing, not passing.

2. **Corpus invariants** — run over all 211 files: every slug equals its filename; every category,
   cuisine and author validates; no file contains `Â`, `â€` or `U+FFFD`; every file ends in exactly
   one newline; the distinct category count is 15 and cuisine count 13.

3. **Output tests** — every recipe produces a page; every page's JSON-LD parses and carries the
   required Recipe fields; `recipes.json` has 211 entries with the FR-022 fields; the corpus is
   byte-identical before and after a build (Principle I, checked by hashing).

**Note on the emitter**: round-trip testing requires an emitter as well as a parser, even though the
site never writes markdown. It exists only for tests and is never wired into the build — Principle I
forbids the build writing to the corpus.

---

## R13. Flattening grouped ingredients into JSON-LD

**Decision**: Settled by clarification — `recipeIngredient` is a flat array of clean ingredient
strings in source order, with group names omitted. Grouping is preserved on the page and in
`recipes.json`.

**Rationale**: `schema.org`'s `recipeIngredient` has no slot for a group name. Prefixing each line
(`"Walnut Cream: 2 cups heavy cream"`) makes every consumer that renders the string verbatim show a
compound that is not an ingredient. Inserting the label as its own array entry puts a non-ingredient
into an array of ingredients, which breaks any consumer counting items or building a shopping list.

`recipeInstructions` uses `HowToSection` containing `HowToStep` when a recipe has named instruction
groups, and a flat `HowToStep` list otherwise — `schema.org` *does* model grouping here, so grouping
is kept where the vocabulary supports it and dropped only where it does not.

---

## R14. Visual continuity with the existing site

**Decision**: Carry forward the existing theme's palette and type — `#4a90e2` primary, `#2c3e50`
secondary, `#f8f9fa` page background, system font stack, white card with a soft shadow — in a single
hand-written stylesheet with a real `@media print` block.

**Rationale**: The family already knows what these recipes look like. A rewrite of the generator is
not a reason to change the look, and matching it keeps the migration invisible to readers. The
existing print affordance opens a new window and rebuilds the document in JavaScript; the
replacement is a `@media print` stylesheet on the page itself, which prints correctly from the
browser's own command, works with JavaScript disabled, and is a fraction of the code (FR-010).

---

## Summary of corrections to the feature prompt

Recorded because each one changes what gets built:

1. **`Total_Time` is never empty** in the corpus — all 211 have a value, not "often empty" (R5).
2. **The vocabulary has no author allowlist**, only a two-entry variant map, so author validation
   must be defined differently from category and cuisine (R4).
3. **A second author misspelling exists** — `Pastrey Living with Anya` — which the prompt does not
   list (R4).
4. **`Authors: TBD` affects 10 recipes** — the same class of defect as `Category: ToTry`, out of the
   stated scope, surfaced for a decision (R4).
5. **The component-label rule needs real design.** A literal port of the reference parser fabricates
   ~200 false headings, including 24 from lines that merely contain spaces (R3).
6. **The mojibake codepage is cp1252, not Latin-1** — the distinction matters for one of the three
   files (R6).
