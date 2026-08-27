---
description: "Task list for feature implementation"
---

# Tasks: Search-First Recipe Site

**Input**: Design documents from `/specs/001-recipe-search-site/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included and **mandatory**. Constitution Principle VII makes parser correctness
fixture-defined, and the Development Workflow section names four quality gates that each require a
test. These are not optional here.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task serves
- Exact file paths are given in every task

## Path Conventions

Single Python project at the repository root: `src/`, `tests/`, `templates/`, `static/`, `tools/`,
with the corpus at `recipes/`. See plan.md → Project Structure.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: An empty but runnable project.

- [X] T001 Initialize the git repository at the repository root with `git init` and a first commit, since GitHub Pages deploys from source and the migration must be reviewable as a diff
- [X] T002 [P] Create `.gitignore` covering `build/`, `.venv/`, `__pycache__/`, `.pytest_cache/`, `*.pyc`
- [X] T003 [P] Create `requirements.txt` pinning `jinja2` and `markdown`, and `requirements-dev.txt` pinning `pytest`
- [X] T004 [P] Create the directory skeleton: `src/`, `templates/`, `static/css/`, `static/js/`, `data/`, `tools/`, `tests/fixtures/`
- [X] T005 [P] Write `README.md` covering what this is, how to build, how to add a recipe, and the rule that the build never modifies `recipes/`
- [X] T006 Create the virtual environment and install both requirements files, confirming `python -c "import jinja2, markdown"` succeeds

**Checkpoint**: `pytest` runs (collecting nothing) and the imports resolve.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The parse and the vocabulary. Every user story consumes these.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T007 Copy `~/code/RecipeScanner/Packages/RecipeKit/Sources/RecipeKit/Generated/vocabulary.json` to `data/vocabulary.json` verbatim, with a header comment in `README.md` recording that it is generated elsewhere and must not be hand-edited
- [X] T008 [P] Copy all three fixture sets from `~/code/RecipeScanner/Packages/RecipeKit/Tests/RecipeKitTests/Fixtures/` into `tests/fixtures/` — `RoundTrip/` (5 files), `Normalisation/` (5 files), `Damage/` (3 files) — byte-for-byte, without repairing anything
- [X] T009 [P] Implement the dataclasses in `src/model.py`: `Recipe`, `ComponentGroup`, `ProseLine`, `TimeRange`, `Violation`, per data-model.md
- [X] T010 [P] Implement `src/vocabulary.py`: load `data/vocabulary.json`, expose `categories`, `cuisines`, `category_variants`, `cuisine_variants`, `author_variants`, `excluded_categories`, and validation functions returning `Violation` objects — never coercing a value (Principle III)
- [X] T011 [P] Implement `src/timeparse.py`: free-text `Total_Time` → `TimeRange | None`, and `TimeRange` → ISO 8601 string, covering every form in research.md R5 (`45 minutes`, `2 hours`, `2 hours 30 minutes`, `2 days`, `3-5 hours`, `overnight`, empty)
- [X] T012 Implement `src/parser.py`: the port of `MarkdownParser.swift` against `contracts/markdown-grammar.md` — front matter to the first blank line, split on the first `:` only, drop the `# ` heading, headnote before the first `##`, sections keyed by `## Name`, and the four-way bare-line classification from research.md R3
- [X] T013 Implement `src/emitter.py`: `Recipe` → markdown, reproducing the exact front-matter key order, the trailing space on empty values, sequential `1. 2. 3.` numbering restarting per group, `## Notes` only when it has content, and exactly one trailing newline. **Used by tests only — never imported by `src/build.py`**
- [X] T014 [P] Write `tests/test_parser.py`: front-matter keys and empty values, the `# ` heading equalling `Title`, headnote capture, grouped and ungrouped sections, absent Notes, and each of the four bare-line classifications
- [X] T015 [P] Write `tests/test_timeparse.py`: every observed form, asserting the range bounds and that ranges and `overnight` yield no ISO 8601 output
- [X] T016 [P] Write `tests/test_vocabulary.py`: a bad category, a bad cuisine, a variant category, an excluded category and a misspelled author each produce a `Violation` naming the file, the value and the correction — and that **all** violations are returned, not just the first
- [X] T017 Write `tests/test_fixtures.py` implementing the three-way split (Principle VII): `RoundTrip/` parse→emit is byte-identical; `Normalisation/` emits the specific corrected form and a byte-identical result is a **failure**; `Damage/` preserves the five published OCR errors in `tk_WalnutSoup.md`

**Checkpoint**: `pytest tests/` passes. The parser is correct against the fixtures before it ever sees the corpus.

---

## Phase 3: User Story 4 — The corpus arrives clean and stays clean (Priority: P1)

**Goal**: 211 recipes in `recipes/`, defects fixed in the files as a reviewable diff, and a build
that validates rather than normalises.

**Independent Test**: Run the migration and confirm no category is outside the 15; introduce a bad
value and confirm the build fails naming file and value; build twice and confirm the corpus bytes
are unchanged.

**⚠️ Ordering note**: This phase precedes the rendering stories because every one of them consumes
the corpus, and a build over the dirty corpus fails validation by design.

- [X] T018 [US4] Write `tools/migrate_corpus.py` with a `--dry-run` flag that prints every proposed change and writes nothing, per the Migration record table in data-model.md
- [X] T019 [US4] Implement the copy step in `tools/migrate_corpus.py`: 211 files from `~/Documents/website/recipes-new/content/recipes/` to `recipes/`, preserving bytes exactly
- [X] T020 [US4] Implement the category corrections in `tools/migrate_corpus.py`: the 27 `ToTry` assignments (6 `Soup`, 11 `Dinner`, 3 `Sides`, 7 `Appetizer`, never `Tapas`), 2 `Sauces`→`Sauce`, 1 `SideS`→`Sides`, and the two files whose category holds a cuisine name
- [X] T021 [US4] Implement the author corrections in `tools/migrate_corpus.py`: `Ottolenghi`→`Yotam Ottolenghi` (2 files) and `Pastrey Living with Anya`→`Pastry Living with Anya` (1 file, found in research.md R4 and absent from the feature prompt)
- [X] T022 [US4] Implement the encoding repair in `tools/migrate_corpus.py`: `text.encode('cp1252').decode('utf-8')` over the damaged runs in `BasqueCheesecake.md`, `SpaghettiPuttanesca.md` and `tk_WalnutSoup.md`, printing each before/after pair, and leaving the other four OCR errors in `tk_WalnutSoup.md` untouched
- [X] T023 [US4] Implement the trailing-newline fix in `tools/migrate_corpus.py`: every file ends with exactly one `\n` (18 files affected)
- [X] T024 [US4] Run `python tools/migrate_corpus.py --dry-run`, present the full change table for confirmation, then run it for real and commit `recipes/` so every correction is a reviewable diff (FR-025, SC-011)
- [X] T025 [US4] Implement validation in `src/build.py`: run every rule from data-model.md over all 211 files, accumulate `Violation`s, print them sorted by file to stderr, and exit `1` writing no output when any exist (FR-030, FR-031, contracts/build-cli.md)
- [X] T026 [P] [US4] Write `tests/test_corpus.py`: over all 211 files — every slug equals its filename, every `# ` heading equals its `Title`, every category/cuisine/author validates, no `Â`/`â€`/`U+FFFD`, every file ends in exactly one newline, distinct categories is 15 and cuisines is 13
- [X] T027 [P] [US4] Write `tests/test_build.py` corpus-integrity case: hash every file in `recipes/`, run a build, re-hash, assert equality (Principle I, SC-007)
- [X] T028 [P] [US4] Add a test asserting `src/build.py` does not import `src/emitter.py`, making the "the build never writes markdown" rule mechanically enforced rather than merely intended

**Checkpoint**: The corpus is clean and committed; the build validates it and refuses anything dirty.

---

## Phase 4: User Story 1 — Read a recipe while cooking (Priority: P1) 🎯 MVP

**Goal**: 211 readable, printable recipe pages with component groups intact.

**Independent Test**: Open any built recipe page directly — title, headnote, grouped ingredients,
grouped instructions and notes all render, and it prints cleanly — with no search page and no index
file present.

- [X] T029 [US1] Write `templates/base.html`: page shell, header, footer, `<meta charset>`, and the block structure the other templates extend
- [X] T030 [US1] Write `templates/recipe.html`: title, summary, meta row (category, cuisine, author, servings, total time), headnote, ingredient groups with component headings, instruction groups with numbering restarting per group, notes only when present (FR-008, FR-009)
- [X] T031 [US1] Render prose lines within a group as paragraphs in `templates/recipe.html`, in source order relative to the group's items, never as headings (data-model.md → `ProseLine`)
- [X] T032 [US1] Write `static/css/site.css` carrying forward the existing palette — `#4a90e2`, `#2c3e50`, `#f8f9fa`, system font stack, white card with soft shadow — with a responsive layout (research.md R14)
- [X] T033 [US1] Add the `@media print` block to `static/css/site.css`: hide header, nav, footer and search controls; drop the card shadow and padding; keep the recipe legible on paper (FR-010)
- [X] T034 [US1] Implement `src/render.py`: set up the Jinja environment with autoescaping, render each `Recipe` through `templates/recipe.html`, and write to `build/<Slug>/index.html` for clean URLs (FR-038, research.md R10)
- [X] T035 [US1] Wire the read → validate → parse → render → write pipeline in `src/build.py` with `--out`, `--strict` and `--no-report` flags and the exit codes in contracts/build-cli.md
- [X] T036 [US1] Implement `src/report.py` writing `build/parse-report.md`: every bare line classified as label or prose, grouped by file, so all 521 decisions are auditable in one artifact (Principle VI, research.md R3)
- [X] T037 [P] [US1] Add rendering cases to `tests/test_build.py`: 211 pages exist; a grouped recipe (`tk_WalnutSoup`) keeps its components in both sections; a recipe without notes (`ApricotUpsideDownCake`) renders no empty Notes heading; a headnote with an italic attribution (`bf_WhiteGazpacho`) survives
- [X] T038 [P] [US1] Add a Unicode fidelity test asserting `¾`, `1 1⁄2` (U+2044), `crème fraîche`, `jalapeño` and `°` appear correctly in built pages (FR-005, SC-001)
- [X] T039 [US1] Run the manual checks in quickstart.md §6 — serve `build/`, open three recipes, and confirm the browser print preview shows recipe content only

**Checkpoint**: A complete, shippable cookbook. MVP reached.

---

## Phase 5: User Story 2 — Find a recipe by what you have (Priority: P1)

**Goal**: The search page is the home page, and it is the only navigation.

**Independent Test**: Load the home page, disconnect the network, then filter by cuisine, by
category and by an ingredient word — each returns the right recipes and every result links to a page
that exists.

**Note**: `recipes.json` is built here rather than in User Story 3 because search depends on it and
this story is the higher priority. US3 then holds it to its public contract.

- [X] T040 [US2] Implement `src/index.py`: `Recipe[]` → `build/recipes.json` per contracts/recipes-json.md — the envelope (`generated`, `count`, `categories`, `cuisines`), the per-recipe fields, the grouped ingredient form, and `time_min`/`time_max` (FR-022)
- [X] T041 [US2] Exclude instructions, notes, headnote and prose lines from the index, per the "Deliberately excluded" section of contracts/recipes-json.md
- [X] T042 [US2] Write `templates/search.html`: the welcome line establishing these are recipes the family likes rather than a comprehensive index, the cuisine/category/time controls, the query input, a result count, and a results container (FR-014, FR-019)
- [X] T043 [US2] Render the full corpus into `templates/search.html` results before any query is entered, so the home page is useful on arrival (FR-014)
- [X] T044 [US2] Implement `static/js/search.js`: fetch `recipes.json`, precompute accent-folded lowercase match keys once at load, and filter on input — no dependencies, no build step (FR-018, research.md R8)
- [X] T045 [US2] Implement combining filters in `static/js/search.js`: cuisine AND category AND free text AND time all narrow together (FR-017)
- [X] T046 [US2] Implement free-text matching over title and ingredient lines in `static/js/search.js`, case-insensitive and accent-folded via `normalize('NFD')` with combining marks stripped, so `creme fraiche` finds `crème fraîche` (FR-015, FR-021)
- [X] T047 [US2] Implement the "under an hour" filter in `static/js/search.js` testing `time_max <= 60`, excluding recipes with no parsed time rather than treating them as zero (FR-016)
- [X] T048 [US2] Implement the result count and the explicit no-matches message in `static/js/search.js` (FR-019)
- [X] T049 [US2] Implement URL state in `static/js/search.js`: read `?q=&cuisine=&category=&time=` on load, `replaceState` while typing, `pushState` on a discrete filter change, and ignore unrecognised values by falling back to the unfiltered corpus (FR-040, research.md R9)
- [X] T050 [US2] Render each result as a link to `/<Slug>` in `static/js/search.js`, showing enough — title, cuisine, category, time — to choose between results (FR-020)
- [X] T051 [US2] Copy `static/` into `build/static/` in `src/build.py`, and write the search page to `build/index.html` as the site root
- [X] T052 [P] [US2] Write `tests/test_index.py`: 211 entries, every FR-022 field present, grouped ingredients retained, no `Â`/`â€`/`U+FFFD` anywhere (FR-024), and every `slug` has a corresponding built page
- [X] T053 [US2] Run the manual search matrix in quickstart.md §7, including the offline check and the shared-URL check (SC-003, SC-013)

**Checkpoint**: The site is complete and usable end to end, locally.

---

## Phase 6: User Story 3 — A machine reads the corpus (Priority: P2)

**Goal**: Every recipe page is machine-readable without parsing HTML, and one artifact answers
whole-corpus questions.

**Independent Test**: Feed built pages to a structured-data validator; fetch `recipes.json` alone
and answer a whole-corpus question from it with no other file.

- [X] T054 [US3] Implement `src/jsonld.py`: `Recipe` → `schema.org/Recipe` dict per contracts/recipe-jsonld.md, covering name, description, datePublished, recipeCategory, recipeCuisine, keywords, author, recipeYield and url
- [X] T055 [US3] Implement flat `recipeIngredient` in `src/jsonld.py`: every ingredient line once, source order, group names dropped, prose lines excluded (FR-013, settled in spec Clarifications)
- [X] T056 [US3] Implement `recipeInstructions` in `src/jsonld.py`: `HowToSection` containing `HowToStep` when a recipe has named instruction groups, a flat `HowToStep[]` otherwise
- [X] T057 [US3] Implement `totalTime` emission in `src/jsonld.py`: ISO 8601 only when the parse is definite; omit for ranges and `overnight` rather than guessing or failing (FR-012)
- [X] T058 [US3] Embed the JSON-LD as `<script type="application/ld+json">` in `templates/recipe.html`, escaped so a title containing `<` or `&` cannot break out of the script element
- [X] T059 [P] [US3] Write `tests/test_jsonld.py`: every page's JSON-LD parses; required Recipe fields present; a grouped recipe flattens every ingredient line exactly once with no group name leaking in; a range-timed recipe omits `totalTime` and is still valid
- [ ] T060 [US3] Submit three built pages to Google's Rich Results test — one grouped (`tk_WalnutSoup`), one flat (`BakedRice`), one without `totalTime` — and confirm zero errors (SC-002)

**Checkpoint**: The corpus is legible to crawlers and agents.

---

## Phase 7: User Story 5 — Publishing is a push (Priority: P2)

**Goal**: A push to the default branch updates `recipes.nateemma.com` with no manual step.

**Independent Test**: Push a change and watch the live site reflect it; push a deliberately invalid
file and watch the deployment refuse to publish.

- [X] T061 [US5] Write `build/CNAME` containing `recipes.nateemma.com` from `src/build.py`, so the custom domain survives every deploy (research.md R10)
- [X] T062 [US5] Write `build/.nojekyll` from `src/build.py`, so Pages serves the output as-is
- [X] T063 [US5] Write `.github/workflows/deploy.yml`: on push to the default branch — checkout, set up Python 3.12, install `requirements.txt`, run `python -m src.build --strict`, `actions/upload-pages-artifact`, `actions/deploy-pages`, with `pages: write` and `id-token: write` permissions and a `pages` concurrency group
- [X] T064 [US5] Add a `pytest` step to `.github/workflows/deploy.yml` before the build, so a parser regression blocks the deploy as surely as a validation failure does
- [ ] T065 [US5] Create the public GitHub repository and push, then confirm the first Actions run completes and the artifact deploys (SC-008)
- [ ] T066 [US5] Verify a failing push does not publish: push a file with an out-of-vocabulary category on a branch, confirm the workflow fails at the build step and the live site is unchanged (FR-036)
- [ ] T067 [US5] Hand the user the two manual, one-time steps that cannot be done from the repository: the `CNAME` DNS record for `recipes.nateemma.com` → `<username>.github.io`, and entering the domain in Settings → Pages with Enforce HTTPS on
- [ ] T068 [US5] Confirm `https://recipes.nateemma.com` loads over HTTPS with a valid certificate, and that the old S3 site is still running and untouched (SC-009, FR-039)

**Checkpoint**: The site is live and self-publishing.

---

## Phase 8: Polish & Cross-Cutting Concerns

- [X] T069 Update `--corpus` in `~/code/RecipeScanner/Makefile` to point at this repository's `recipes/`, and confirm `make vocab` still runs there (FR-041, SC-014)
- [X] T070 Confirm `data/vocabulary.json` was **not** regenerated by this work, and record in `README.md` that regenerating it is RecipeScanner's decision (FR-042)
- [X] T071 Read `build/parse-report.md` end to end and confirm no sentence became a heading and no genuine label was demoted to prose (Principle VI)
- [ ] T072 [P] Surface the two findings the feature prompt did not anticipate for a decision: `Authors: TBD` on 10 recipes, and the ~10 `bf_` files whose OCR damage no label rule can recover (research.md R4, R3)
- [X] T073 [P] Add a `Makefile` or `justfile` with `build`, `test`, `serve` and `migrate` targets so the common commands are discoverable
- [X] T074 [P] Confirm the generated site contains no taxonomy browse or index pages and no Stork artifact (FR-032, SC-012)
- [X] T075 Measure and record: full build time, `recipes.json` size, and search latency for the whole corpus, against SC-004 and SC-010
- [ ] T076 Delete the old corpus copy at `~/Documents/website/recipes-new/content/recipes/` once the move is verified, leaving the rest of `recipes-new/` on disk as the archive (spec Assumptions, settled decision 1)
- [X] T077 Run the full quickstart.md end to end as a final acceptance pass

---

## Dependencies

```text
Phase 1 Setup
     ↓
Phase 2 Foundational  ← parser + vocabulary + fixtures. BLOCKS EVERYTHING.
     ↓
Phase 3 US4 Migration ← the corpus must be clean before any build succeeds
     ↓
Phase 4 US1 Recipe pages  🎯 MVP
     ↓
Phase 5 US2 Search ────────┐  (builds recipes.json)
     ↓                     │
Phase 6 US3 JSON-LD  ←─────┘  (US3's index work depends on T040)
     ↓
Phase 7 US5 Deploy    ← needs a complete site to publish
     ↓
Phase 8 Polish
```

**Story independence after Phase 3**: US1 is genuinely standalone — it needs no index and no search.
US2 depends on US1 only for the pages its results link to. US3's JSON-LD half is independent of US2;
its index half is the same `recipes.json` US2 builds. US5 needs a site to publish but is indifferent
to which stories produced it.

**Hard sequencing**: T012 (parser) blocks everything downstream. T024 (migration applied) blocks
every successful build. T040 (`recipes.json`) blocks T044–T050.

## Parallel Execution Examples

**Phase 2** — after T009 lands, these four are independent files:

```text
T010 src/vocabulary.py    T011 src/timeparse.py
T014 tests/test_parser.py T015 tests/test_timeparse.py
```

**Phase 3** — after T025:

```text
T026 tests/test_corpus.py   T027 corpus-integrity case   T028 import-guard test
```

**Phase 4** — after T035:

```text
T037 rendering cases   T038 Unicode fidelity test
```

**Phase 8** — T072, T073 and T074 touch nothing in common.

## Independent Test Criteria

| Story | Verified by |
|---|---|
| **US4** Clean corpus | quickstart.md §1, §3, §4 — 15 categories, byte-identical corpus, loud failure |
| **US1** Read a recipe | quickstart.md §6 — three recipes render, print preview is clean |
| **US2** Find a recipe | quickstart.md §7 — the search matrix, offline and shared-URL included |
| **US3** Machine reads | quickstart.md §8 — JSON-LD parses on every page, Rich Results clean |
| **US5** Push publishes | quickstart.md §10 — a push updates the live site, a bad push does not |

## Implementation Strategy

**MVP = Phases 1–4** (T001–T039). That yields a clean, committed corpus and 211 readable, printable
recipe pages — a usable cookbook with no search. The spec calls this out explicitly: a site that
renders recipes well and has no search is still a usable cookbook.

**Then Phase 5** makes it navigable, which is the point of the rewrite.

**Then Phases 6–7** make it public and machine-legible.

**Two decision points that stop for a human** (Principle VI):

- **T024** — the migration change table is presented before it is applied. Two of the 27 assignments
  are proposals rather than settled: `bf_TunaCevichePineapple` and `bf_YucatanChickenWraps`, whose
  categories the feature prompt records as "simply missing" without saying what they should be.
- **T072** — `Authors: TBD` on 10 recipes, and the OCR-damaged `bf_` files, are surfaced for a
  decision rather than fixed or ignored.
