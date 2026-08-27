# Price Family Recipes

A static site for the family recipe collection, at **[recipes.nateemma.com](https://recipes.nateemma.com)**.

Search is the only navigation. There are no category or cuisine browse pages — one search box over
the whole corpus replaces them.

## What is here

| Path | What it is |
|---|---|
| `recipes/` | **The corpus.** 211 markdown files. The only source of truth. |
| `src/` | The generator. Reads the corpus, writes `build/`. Never writes to `recipes/`. |
| `templates/`, `static/` | Jinja templates, one stylesheet, one search script. |
| `data/vocabulary.json` | The shared category/cuisine/author vocabulary. **Generated elsewhere.** |
| `tests/` | Parser fixtures, corpus invariants, output checks. |
| `tools/migrate_corpus.py` | One-time corpus migration. Not part of the build. |

## Build

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
python -m src.build
python -m http.server 8000 --directory build
```

## Adding a recipe

Drop a `.md` file into `recipes/` and push. The site rebuilds and deploys itself.

The file format is **not ours to change** — it is the output format of
[RecipeScanner](https://github.com/) , an iOS app with byte-level round-trip tests against this same
corpus. Bare `Key: value` front matter with no `---` fences, then `# Title`, an optional headnote,
`## Ingredients`, `## Instructions`, and `## Notes` only when it has content.

## Two rules worth knowing

**The build never modifies `recipes/`.** Derived output is disposable; the markdown is not. A test
hashes every file before and after a build and fails if anything moved.

**The build validates, it does not normalise.** A `Category`, `Cuisine` or `Author` outside the
shared vocabulary fails the build, names the file and the value, and writes nothing. It will tell you
that `Sauces` should be `Sauce` — it will not quietly write it for you. Fix the file; the data should
be right where it lives.

## `data/vocabulary.json` is generated

Do not edit it by hand. It is produced by `make vocab` in the RecipeScanner repository, whose
`--corpus` argument points at this repository's `recipes/`. Regenerating it is that project's
decision, not this one's: a regeneration empties its variant maps and reorders a generated Swift
enum, which is correct but belongs in a deliberate change over there.

## Design notes

The full specification, plan and research live in `specs/001-recipe-search-site/`. The two findings
most likely to surprise someone reading the code:

- **Authors have no allowlist.** The vocabulary closes `Category` and `Cuisine` but not `Authors`,
  which is right — authors are an open set. Validation rejects known misspellings and passes anything
  else.
- **A bare line inside a section is not always a component label.** Treating every one as a label
  fabricates ~200 false headings on this corpus. See `research.md` R3 for the rule and the counts.
