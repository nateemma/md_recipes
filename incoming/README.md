# incoming/

A staging area for recipes on their way into the corpus.

Drop `.md` files here — exported from RecipeScanner, or written by hand from
`docs/recipe-template.md` — and run:

```bash
make import      # shows what it found and validates it; copies nothing
make import-go   # copies them into recipes/
```

The import also looks in `~/Downloads`, which is where RecipeScanner's share
sheet puts things, so you can skip this directory entirely if that suits you
better.

## Why not just copy into recipes/ yourself

You can, and RecipeScanner's output will pass validation. The one thing `cp`
will not tell you is that the slug already exists — it overwrites, and the
recipe that was there is gone unless git has it. The import refuses to do that
without `--replace`, and validates the whole corpus with the new files staged in
before it copies anything, so a bad file never lands in `recipes/` at all.

## This directory is not published

Everything here except this README is git-ignored. Files left behind are
harmless: they are not part of the corpus, not validated, and not built. Use
`make import-go` with `--move` if you would rather it emptied itself.
