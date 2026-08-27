# Implementation Plan: Search-First Recipe Site

**Branch**: `001-recipe-search-site` | **Date**: 2026-08-26 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-recipe-search-site/spec.md`

## Summary

Move 211 markdown recipes into this repository, cleaning the known defects as they move, and
replace the Pelican site that renders them with a single-purpose Python generator. The generator
parses each recipe once into structure — front matter, headnote, ingredient groups, instruction
groups, notes — and feeds that one parse to three consumers: a printable recipe page per recipe
carrying `schema.org/Recipe` JSON-LD, a search page that is the home page, and one `recipes.json`
covering the whole corpus. Search is the only navigation; every taxonomy browse page is deleted.
The build validates against the shared vocabulary and fails loudly rather than normalising, and
never writes to the corpus. A push to the default branch publishes to GitHub Pages at
`recipes.nateemma.com`.

The technical approach is settled in [research.md](./research.md). Its two consequential findings:
the vocabulary has **no author allowlist**, so author validation is defined against the variant map
rather than a closed list (R4); and the reference parser's component-label rule, ported literally,
fabricates roughly 200 false headings on this corpus, so the label rule needs real design plus an
audit report (R3).

## Technical Context

**Language/Version**: Python 3.12 (3.11+ supported). No JavaScript toolchain — the browser code is
hand-written ES2020, served as-is.

**Primary Dependencies**: `jinja2` (templating and HTML escaping), `markdown` (headnote, notes and
inline prose). `pytest` for tests. Nothing else at runtime; no bundler, no CSS framework, no search
library.

**Storage**: The markdown corpus in `recipes/` — flat files, read-only to the build. No database.
Generated output in `build/`, which is disposable and git-ignored.

**Testing**: `pytest`. Three fixture sets copied from RecipeScanner (`RoundTrip/`, `Normalisation/`,
`Damage/`), corpus-wide invariants over all 211 files, and output assertions over the built site.

**Target Platform**: Static files on GitHub Pages, custom domain `recipes.nateemma.com`. Readers on
current desktop and mobile browsers; recipe pages readable with JavaScript disabled, search not.

**Project Type**: Static site generator — a CLI build tool plus the site it emits.

**Performance Goals**: Full build under 5 s for 211 recipes. Search results within 100 ms of a
keystroke (SC-004); home page interactive within 2 s on a normal connection. `recipes.json` under
500 KB uncompressed.

**Constraints**: The corpus is byte-immutable to the build (Principle I). The markdown format is a
fixed external contract (Principle II). No server, no query backend, no build step for browser code.
Unicode fidelity — vulgar fractions, U+2044 fraction slash, accents, `°` — end to end.

**Scale/Scope**: 211 recipes today, designed to stay comfortable to several times that. 1 search
page, 0 images, 0 feeds. Roughly 1,200 lines of Python plus templates, CSS and one JavaScript file.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Evaluated against [Constitution v1.0.0](../../.specify/memory/constitution.md).

| Principle | Design response | Gate |
|---|---|---|
| **I. Corpus is the only source of truth** | The build opens corpus files read-only. The emitter exists solely for round-trip tests and is never called by `build.py`. A test hashes every corpus file before and after a build and asserts equality. | **PASS** |
| **II. Grammar is a fixed external contract** | `parser.py` is a port of `MarkdownParser.swift` against `markdown-output.md`. No format change, no extension. Divergences are documented in `contracts/markdown-grammar.md` with the contract text they implement. | **PASS** — see note |
| **III. Validate, never normalise** | `vocabulary.py` checks category and cuisine against the closed lists and authors against the variant map. Violations accumulate and are reported together; a non-empty violation list exits non-zero before any file is written. | **PASS** |
| **IV. One parse, many consumers** | `parser.py` produces a `Recipe` dataclass. `render.py`, `jsonld.py` and `index.py` all take that object. No consumer touches markdown text or rendered HTML. | **PASS** |
| **V. Small and inspectable over framework** | Pelican removed. Two runtime dependencies, each justified in R1/R2. No plugin mechanism, no abstraction layer, no configuration system. | **PASS** |
| **VI. Human-in-the-loop for ambiguous data** | The 27 category assignments are proposed as a reviewable table before being applied. `build/parse-report.md` exposes all 521 label/prose classifications for audit. Three findings the prompt did not anticipate — the second author misspelling, `Authors: TBD` on 10 recipes, the OCR-damaged `bf_` files — are surfaced, not silently decided. | **PASS** |
| **VII. Parser correctness is fixture-defined** | The three fixture sets are copied in and drive `test_fixtures.py`. `Normalisation/` asserts the corrected output, so a parser that round-trips a dirty file fails. | **PASS** |
| **Publishing** | One workflow, push-triggered, no manual step, no second repository. Validation failure blocks the deploy step by exiting non-zero. | **PASS** |
| **Quality gates** | Corpus integrity, vocabulary, structured-data, and fixture gates each have a named test. Cross-project consequences are called out in `contracts/` and in the tasks. | **PASS** |

**Note on Principle II** — one deliberate divergence from the *reference implementation*, which is
not a divergence from the *contract*. The Swift parser treats any bare non-list line as a component
label. The written contract defines a label as "its label as a bare line, then a blank line, then its
own list". On this corpus the implementation's shortcut produces ~200 false headings (R3), including
24 from whitespace-only lines. This plan follows the written contract and adds a structural test.
This changes no file, no format and no emitted byte, so RecipeScanner's round-trip tests are
unaffected. It is recorded in Complexity Tracking for visibility.

**Post-Phase 1 re-check**: Re-evaluated after `data-model.md` and `contracts/` were written. All
gates still **PASS**. The design added no dependency, no framework, and no write path to the corpus.
The one structure added since the gate — `ProseLine` in the group model — exists precisely to avoid
fabricating headings, which serves Principle VI rather than straining it.

## Project Structure

### Documentation (this feature)

```text
specs/001-recipe-search-site/
├── plan.md                       # This file
├── spec.md                       # Feature specification
├── research.md                   # Phase 0 output
├── data-model.md                 # Phase 1 output
├── quickstart.md                 # Phase 1 output
├── contracts/                    # Phase 1 output
│   ├── markdown-grammar.md       # The ported parse, and where it is authoritative
│   ├── recipes-json.md           # Index schema — the agent-facing artifact
│   ├── recipe-jsonld.md          # schema.org/Recipe mapping
│   └── build-cli.md              # Build command, exit codes, failure output
├── checklists/
│   └── requirements.md           # Spec quality checklist
└── tasks.md                      # Phase 2 output (/speckit-tasks — not created here)
```

### Source Code (repository root)

```text
recipes/                          # THE CORPUS — 211 .md files. Read-only to the build.
                                  # Arrives via migration, cleaned once, as a reviewable diff.

src/
├── build.py                      # Entry point: read → validate → parse → render → write
├── parser.py                     # Port of MarkdownParser.swift. The centre of the program.
├── emitter.py                    # Markdown emitter — TESTS ONLY, never called by build.py
├── model.py                      # Recipe, ComponentGroup, ProseLine, TimeRange dataclasses
├── vocabulary.py                 # Loads vocabulary.json; validates category/cuisine/author
├── timeparse.py                  # Free-text Total_Time → (min, max) minutes → ISO 8601
├── jsonld.py                     # Recipe → schema.org/Recipe JSON-LD
├── index.py                      # Recipe[] → recipes.json
└── report.py                     # build/parse-report.md — the label/prose audit

templates/
├── base.html                     # Shell: header, footer, print rules
├── recipe.html                   # One recipe: headnote, groups, notes, JSON-LD
└── search.html                   # The home page: welcome, filters, results

static/
├── css/site.css                  # One stylesheet, including @media print
└── js/search.js                  # Filter + render. No dependencies, no build step.

data/
└── vocabulary.json               # Copied from RecipeScanner. Do not edit by hand.

tests/
├── fixtures/
│   ├── RoundTrip/                # 5 files — parse→emit must be byte-identical
│   ├── Normalisation/            # 5 files — must emit a specific corrected form
│   └── Damage/                   # 3 files — published OCR errors must survive
├── test_parser.py                # Grammar: front matter, groups, headnote, notes
├── test_fixtures.py              # The three-way split (Principle VII)
├── test_corpus.py                # Invariants over all 211 files
├── test_vocabulary.py            # Validation fails correctly, reports every violation
├── test_timeparse.py             # Every observed Total_Time form
├── test_jsonld.py                # Required fields, flattening, omitted totalTime
├── test_index.py                 # recipes.json shape and completeness
└── test_build.py                 # Output exists; corpus byte-identical after build

tools/
└── migrate_corpus.py             # ONE-TIME: copy + clean. Not part of the build.

.github/workflows/deploy.yml      # push → build → upload-pages-artifact → deploy-pages
requirements.txt                  # jinja2, markdown
requirements-dev.txt              # pytest
build/                            # Generated output. Git-ignored.
├── index.html                    # The search page
├── recipes.json                  # The index
├── <Slug>/index.html             # 211 recipe pages — clean URLs
├── static/
├── CNAME                         # recipes.nateemma.com
├── .nojekyll
└── parse-report.md               # Audit artifact, not published
```

**Structure Decision**: A single Python project at the repository root — the default layout, with
`src/` for the generator, `tests/` beside it, and the corpus as a first-class top-level directory
rather than buried under `content/`. There is no frontend/backend split because there is no backend;
the browser code is two files served verbatim, so it lives in `static/` rather than in a project of
its own.

`tools/migrate_corpus.py` is deliberately outside `src/`: it runs once, it *writes* to the corpus,
and Principle I forbids that of anything in the build path. The separation is the enforcement.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Component-label rule diverges from the reference *implementation* (not the contract) | The Swift shortcut "any bare non-list line is a label" fabricates ~200 false headings on this corpus — 24 of them from lines containing only spaces, 92 from OCR-wrapped sentences. On a web page each is a visible wrong `<h3>`. | A literal port was tried first and measured (R3). It is correct for its own purpose — round-trip testing, where a false label round-trips harmlessly — but not for rendering. Requiring a trailing colon instead was also rejected: it loses 133 genuine labels. The chosen rule emits no byte into any markdown file, so RecipeScanner is unaffected. |
| A `ProseLine` type in the group model | 89 corpus lines are neither list items nor labels — OCR-wrapped sentence fragments and stray remarks. They must render as prose. | Dropping them loses content. Appending them to the previous item guesses at intent and corrupts the cases where the line is a genuine separate remark. Both violate Principle VI. |
| An emitter that the site never uses | Round-trip and normalisation fixtures (Principle VII) cannot be asserted without re-emitting. | There is no way to test "parse → emit → byte-identical" without an emitter. It is isolated in `emitter.py`, imported only by tests, and its absence from `build.py`'s imports is itself assertable. |
