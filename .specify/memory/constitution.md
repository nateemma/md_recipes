<!--
Sync Impact Report
==================
Version change: (unversioned template) → 1.0.0
Bump rationale: MAJOR — initial ratification. The file previously held only unfilled
template placeholders, so this establishes governance where none existed.

Modified principles: none (no prior principles existed)

Added sections:
  - Core Principles I–VII
  - Publishing and Deployment
  - Development Workflow and Quality Gates
  - Governance

Removed sections: none

Templates reviewed for consistency:
  - .specify/templates/plan-template.md — Constitution Check gate reads this file at runtime; no edit needed
  - .specify/templates/spec-template.md — no constitution references; no edit needed
  - .specify/templates/tasks-template.md — no constitution references; no edit needed

Follow-up TODOs: none. RATIFICATION_DATE is the date of this initial adoption.
-->

# md_recipes Constitution

## Core Principles

### I. The Corpus Is the Only Source of Truth (NON-NEGOTIABLE)

The markdown recipe files in `recipes/` are the single authoritative representation of every
recipe. The build MUST treat them as read-only input: it MUST NOT rewrite, reformat, reorder,
re-encode or touch them in any way. Every published artifact — recipe pages, structured data, the
search index — is derived output that MAY be deleted and regenerated at any time without loss.

Corrections belong in the files. Where data is wrong, it is fixed once, at rest, as a reviewable
diff — never patched on the fly during a build.

**Rationale**: A build that edits its own input has no reproducible state and no reviewable
history. Byte-stability of the corpus is directly testable: build twice, compare bytes.

### II. The Markdown Grammar Is a Fixed External Contract

The recipe file format — bare `Key: value` front matter with no fences, in a fixed key order,
followed by `# Title`, optional headnote, `## Ingredients`, `## Instructions`, and `## Notes` only
when it has content — is owned by the RecipeScanner project, which holds byte-level round-trip
tests against this same corpus. This project MUST NOT change the format, extend it, or introduce
a variant.

The grammar is **ported, not reinvented**: the authoritative contract document and the reference
parser in RecipeScanner define the parse, and any disagreement between this project's parser and
that reference is a defect in this project until proven otherwise.

**Rationale**: Two independent programs write and read the same files. A unilateral format change
here silently breaks an app that has already shipped.

### III. Validate, Never Normalise

The build MUST check every `Category`, `Cuisine` and `Author` value against the shared vocabulary
table and MUST fail when a value falls outside it, naming the offending file and the offending
value. The build MUST NOT silently map, coerce, correct or drop an unknown value.

Validation MUST report every violation in a single run rather than stopping at the first, and MUST
write no site output when it fails.

**Rationale**: Normalisation hides a defect forever — the file stays wrong and nobody learns. A
loud failure keeps the corpus clean as it grows, at the cost of one obvious fix per bad file.

### IV. One Parse, Many Consumers

Each recipe MUST be parsed exactly once, into structure — front-matter fields, headnote, ingredient
groups, instruction groups, notes. The recipe templates, the `schema.org/Recipe` JSON-LD and the
search index MUST all be consumers of that one parsed representation. No consumer may re-parse
markdown, scrape rendered HTML, or maintain a second, divergent understanding of a recipe.

A component group is an optionally named part carrying its own ordered lines, exactly one level
deep, never nested, preserving source order.

**Rationale**: Three parsers drift. When the page, the structured data and the index disagree about
a recipe, the machine-readable ones are wrong in the least visible way.

### V. Small and Inspectable Over Framework

Prefer a direct generator that a reader can hold in their head — read the corpus, parse, render
through a template, write the index, write the search page — over a framework whose behaviour is
configured rather than written. Dependencies MUST be justified by what they actually do here, not
by what they might allow later.

Adding a dependency, an abstraction layer, or a plugin mechanism requires a stated reason in the
implementation plan's Complexity Tracking section. "We might need it" is not a reason.

**Rationale**: The whole site is a few hundred recipes, one search page and no images. The parser
is the interesting part of this program and belongs at its centre, not inside a framework hook.

### VI. Human-in-the-Loop for Ambiguous Data

Where a data correction is genuinely ambiguous — which category a small Spanish plate belongs to,
what a damaged character was meant to be — the system MUST propose and ask rather than decide
silently. Corrections that are obvious from the recipe itself MAY be inferred, but MUST still be
presented as a reviewable diff.

This mirrors the rule RecipeScanner works to, and applies to any future bulk corpus change, not
only the initial migration.

**Rationale**: A silently guessed category is indistinguishable from a correct one and will never
be revisited. Asking costs minutes once; a wrong guess is permanent.

### VII. Parser Correctness Is Fixture-Defined

Expected parser behaviour is defined by three distinct fixture sets, reused from RecipeScanner:

- **RoundTrip** — files that MUST re-emit byte-identically.
- **Normalisation** — files that MUST produce a specific *corrected* output.
- **Damage** — files carrying real published errors that MUST be preserved exactly, not repaired.

A parser that round-trips a Normalisation fixture unchanged is failing, not passing. Fixtures are
committed copies and do not change when the live corpus changes.

**Rationale**: "Round-trips perfectly" is the wrong success criterion on a corpus that contains
known defects. The three-way split is what makes correctness stateable at all.

## Publishing and Deployment

Publishing MUST be automatic: a push to the default branch builds and updates the live site with no
manual build, no manual upload, and no second repository of built output. A build that fails
validation MUST NOT publish, and the failure MUST be visible.

The site is served over HTTPS at its custom domain with a platform-managed certificate. Deployment
infrastructure MUST stay at the minimum the platform requires — no additional accounts, roles,
distributions or invalidation steps.

Generated URLs MUST NOT require a file extension. The previously published site is left running and
untouched until the new one is deliberately retired.

## Development Workflow and Quality Gates

- **Corpus integrity gate**: the corpus MUST be byte-identical before and after any build. This is
  verified, not assumed.
- **Vocabulary gate**: no published `Category`, `Cuisine` or `Author` value may fall outside the
  shared vocabulary. Introducing a new vocabulary value is a change to RecipeScanner first, and
  reaches this project only through a regenerated table.
- **Structured-data gate**: every recipe page MUST carry valid `schema.org/Recipe` JSON-LD.
- **Fixture gate**: the three fixture sets of Principle VII MUST pass before any change to the
  parser is considered complete.
- **Cross-project awareness**: changes here that reach into RecipeScanner — corpus path, vocabulary
  regeneration, variant maps, generated enum ordering — MUST be called out explicitly rather than
  discovered by the other project's build breaking.
- Every corpus correction is reviewed as a diff. Bulk edits without a diff to read are not
  acceptable.

## Governance

This constitution supersedes other conventions in this repository. Where a plan, task list or
review conflicts with it, the constitution wins or the constitution is amended first — not
silently overridden.

**Amendment procedure**: amendments are made by editing this file with a Sync Impact Report
recording the version change, the principles affected, and any templates needing follow-up. An
amendment that removes or redefines a principle MUST state what replaces it.

**Versioning policy**: semantic versioning.
- **MAJOR** — a principle is removed, or redefined in a way that invalidates prior compliance.
- **MINOR** — a principle or section is added, or guidance is materially expanded.
- **PATCH** — clarification, wording, or non-semantic refinement.

**Compliance review**: `/speckit-plan` MUST evaluate its design against these principles at its
Constitution Check gate, and any violation MUST appear in Complexity Tracking with a justification
and the simpler alternative that was rejected. Unjustifiable violations block the plan rather than
being noted and passed.

**Version**: 1.0.0 | **Ratified**: 2026-08-26 | **Last Amended**: 2026-08-26
