# Contract: Markdown Grammar (consumed)

**Provider**: `RecipeKit.MarkdownEmitter` (RecipeScanner) | **Consumer**: this project's `parser.py`

This project does **not** own this format (Constitution Principle II). The authority is
`~/code/RecipeScanner/specs/001-scan-cookbook-recipe/contracts/markdown-output.md`, and the
reference implementation is `MarkdownParser.swift` in the same repository. This file records what
`parser.py` must implement and the one place it deliberately follows the written contract rather
than the reference implementation.

## Grammar

```
file            := front-matter blank-line title-heading headnote? ingredients instructions notes?
front-matter    := key-line+ blank-line          # bare Key: value, NO --- fences
key-line        := KEY ": " value NEWLINE
title-heading   := "# " title NEWLINE blank-line
ingredients     := "## Ingredients" NEWLINE blank-line group+
instructions    := "## Instructions" NEWLINE blank-line group+
notes           := "## Notes" NEWLINE blank-line note-line*
group           := label-line? blank-line? item+
```

## Front matter

Exact keys, exact order: `Title`, `Summary`, `Date`, `Slug`, `Category`, `Cuisine`, `Tags`,
`Authors`, `Total_Time`, `Servings`.

- Front matter runs to the **first blank line**.
- Split each line on the **first** `:` only; strip whitespace from the value.
- A key is emitted even when empty, **with a trailing space** — `"Tags: "`. Round-trip equality is
  measured against that trailing space; the parser must not require it and the emitter must produce
  it.
- `Date` is `YYYY-MM-DD HH:MM` — a **space, not `T`**, and no timezone.
- `Slug` matches `^[A-Za-z0-9_]+$` and equals the filename without `.md`.
- `Tags` is comma-space separated; empty value → empty list.

## Body

- Skip blank lines after the front matter, then drop the `# ` heading. Its text must equal `Title`.
- Lines before the first `##` are the **headnote** — joined with `\n`, then stripped. May be several
  paragraphs and may include an italic attribution line (`Adapted from *Bobby Flay: Chapter One*`).
- `## <Name>` opens a section. Only `Ingredients`, `Instructions` and `Notes` are meaningful.
- `## Notes` is present **only when it has content** — 54 of 211 recipes have no Notes section.
  Rendering an empty heading breaks round-trip on a quarter of the corpus.
- Ingredients are `- ` bullets. Instructions are `N. ` ordered items. Notes are `- ` bullets.
- Ordered numbering **restarts at 1 within each group**.

## Component groups

A labelled group is its label as a bare line, then a blank line, then its own list. An unlabelled
group emits no label line and no extra blank line. One level deep, never nested. The same component
names recur across `## Ingredients` and `## Instructions`.

### The one divergence — bare-line classification

The reference *implementation* treats **any** bare non-list line as a label. The written *contract*
defines a label structurally: "its label as a bare line, then a blank line, then its own list".

Measured over the corpus, the implementation's shortcut fabricates roughly 200 false headings from
521 bare lines — 24 from whitespace-only lines (which are not `isEmpty` in Swift), and 92 from
OCR-wrapped sentence fragments in the `bf_` import. `parser.py` therefore implements the written
contract, classifying each bare line in order:

1. Whitespace-only → **discard**.
2. Ends with `:` after stripping surrounding `**` → **label**.
3. Next non-blank line in the section is a list item, AND length ≤ 60, AND does not end in `.`
   → **label**.
4. Otherwise → **prose line**, attached to the current group and rendered as a paragraph.

**This divergence emits no byte into any markdown file.** It affects only how this project renders
what it reads, so RecipeScanner's round-trip and normalisation tests are unaffected. See
`research.md` R3 for the measurements and the rejected alternatives.

## Encoding

- UTF-8, no BOM, LF line endings, ending in **exactly one** newline.
- Vulgar fractions (`½ ¼ ¾ ⅓`), U+2044 fraction slash, `°` and accents pass through unchanged.
- `U+FFFD`, `Â` or `â€` anywhere in a file is a **validation failure**, not a warning.

## Test obligations (Principle VII)

| Fixture set | Files | Assertion |
|---|---:|---|
| `RoundTrip/` | 5 | parse → emit → **byte-identical** |
| `Normalisation/` | 5 | emit the specific **corrected** form. A file that round-trips unchanged is a **failure**. |
| `Damage/` | 3 | the five published OCR errors **survive** parsing untouched |

`Normalisation/` includes `bf_WhiteGazpacho.md` (two items numbered `1.`, plus an unmarked
continuation line) and `BroccoliSalad.md` (no trailing newline).

## Cross-project consequences (FR-041, FR-042)

- RecipeScanner's `Makefile` locates the corpus by path for `make vocab`. Moving the corpus breaks
  it; the path must be updated to this repository's `recipes/` as part of this feature.
- `vocabulary.json` is **copied, not regenerated**, by this feature. Regenerating it would empty
  `categoryVariants` and reorder the generated Swift enum — correct, but the other project's call.
- The three fixture sets are **committed copies** and do not change when this corpus changes.
  `Damage/tk_WalnutSoup.md` keeps all five OCR errors even though the published file has its
  encoding damage repaired.
