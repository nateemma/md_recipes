# Status

_Last updated: 2026-10-08_

## Summary

The recipe search site is built and live. The remaining work is cleanup.

## Build

- Spec: `specs/001-recipe-search-site/`
- Tasks: 76 of 77 done (`specs/001-recipe-search-site/tasks.md`)

## Deploy

- The "Build and deploy" GitHub workflow (`.github/workflows/deploy.yml`) runs on every push to `main`.
- The last three runs passed; the most recent was 2026-10-08.

## Corpus

- 322 recipes in `recipes/`
- New recipes come in through `incoming/`, using `make import` and then `make import-go` (see `incoming/README.md`).

## Open items

- [ ] **T076**: Delete the old copy of the recipes at `~/Documents/website/recipes-new/content/recipes/`, once the move has been checked. Keep the rest of `recipes-new/` as the archive.
- [x] Clear `incoming/`: removed the 14 `jg_*.md` copies that had already been imported (2026-10-08).
