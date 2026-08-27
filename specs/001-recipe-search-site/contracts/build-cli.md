# Contract: Build CLI (provided)

**Provider**: `src/build.py` | **Consumers**: a developer, and `.github/workflows/deploy.yml`

## Invocation

```
python -m src.build [--out build] [--strict] [--no-report]
```

| Flag | Default | Meaning |
|---|---|---|
| `--out` | `build` | Output directory. Emptied of generated files first; the corpus is never touched. |
| `--strict` | on in CI | Treat warnings as errors. |
| `--no-report` | off | Skip `parse-report.md`. |

## Exit codes

| Code | Meaning | Output written |
|---|---|---|
| `0` | Success | Full site |
| `1` | Validation failed — a category, cuisine, author, slug, title, encoding or trailing-newline violation | **None** (FR-030) |
| `2` | Parse failure — a file that is not a recipe | **None** |
| `3` | I/O failure | Partial; the build says so |

Exit `1` is what blocks a bad push from publishing (FR-036): the workflow's build step fails before
`deploy-pages` runs, so the live site is unchanged.

## Failure output

Every violation, sorted by file, one per line on stderr — never just the first (FR-031):

```
recipes/bf_Cioppino.md: Category: 'ToTry' is not a category (it is a workflow state; excluded)
recipes/GreekHarissa.md: Category: 'Sauces' is not in the vocabulary — did you mean 'Sauce'?
recipes/tk_WalnutSoup.md: Authors: 'Ottolenghi' is a known misspelling of 'Yotam Ottolenghi'
recipes/BasqueCheesecake.md:44: Encoding: damaged text '8â€³' — repair to '8″'
recipes/BroccoliSalad.md: file does not end with a newline

5 violations in 4 files. No output written.
```

Each line carries the file, the field, the offending value, and — where the vocabulary knows it —
the correction. That is what makes the failure fixable without further searching (SC-006). The build
**states** the correction; it never **applies** it (Principle III).

## Guarantees

- **The corpus is never written to** (Principle I). Verified by hashing every file before and after.
- Output is deterministic apart from `recipes.json`'s `generated` timestamp.
- A run that exits non-zero writes no site output, so a partial site is never deployed.
