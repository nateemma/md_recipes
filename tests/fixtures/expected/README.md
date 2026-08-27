# Expected normalisation output

The three fixture sets in `RoundTrip/`, `Normalisation/` and `Damage/` are **byte-identical
copies** from RecipeScanner and must not be edited here.

This directory holds *this project's* assertion about what each `Normalisation/` fixture emits —
the "specific corrected output" that Constitution Principle VII requires. Each file was generated
once, reviewed line by line against the source, and committed.

| Fixture | Correction asserted |
|---|---|
| `BroccoliSalad.md` | Gains its missing trailing newline. |
| `GreekHarissa.md` | Blank lines between ordered items removed; the triple trailing newline collapses to one. |
| `SpaghettiBolognese.md` | Source numbering skips `12.` (goes 11 → 13); renumbered sequentially. |
| `bf_WhiteGazpacho.md` | The documented quirk — two items numbered `1.` renumbered to `1. 2. 3.`, the unmarked continuation line kept as prose, extra blank lines collapsed, and an empty `## Notes` section dropped. |
| `Succotash.md` | **No format change.** Its only defect is `Category: SideS`, which is a *vocabulary* defect. |

## Why `Succotash.md` is unchanged here but changes in RecipeScanner

RecipeScanner's parser maps vocabulary variants at read time (`VocabularyMap.category`), so its
emitter writes `Sides` and the file changes. This project must not do that: Constitution
Principle III is *validate, never normalise*. A vocabulary defect is fixed once, in migration, and
thereafter **fails the build** — it is never silently rewritten.

So the two projects normalise different things, deliberately:

- **RecipeScanner's emitter** corrects format defects *and* vocabulary defects.
- **This project's emitter** corrects format defects only, and exists solely for these tests.
