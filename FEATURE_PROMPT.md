# Feature prompt — md_recipes

Feed the **Description** section to `/speckit-specify`. Everything after it is context for the
plan and task phases.

---

## Description

Build a static site for the Price Family Recipes collection, generated from a directory of
markdown recipe files, where **search is the only navigation** and publishing is automatic.

The corpus is 211 markdown files with bare `Key: value` front matter — no `---` fences —
followed by `# Title`, optional prose, `## Ingredients`, `## Instructions`, and an optional
`## Notes`. That format is a fixed contract this project must not change: it is the output
format of a separate iOS app, RecipeScanner, which has byte-level round-trip tests against the
same corpus.

The site has three parts and nothing else:

1. **A recipe page per recipe.** Readable, printable, carrying `schema.org/Recipe` JSON-LD so
   agents and crawlers can consume it without parsing HTML.

2. **A search page, which is the home page**, opening with a line or two of welcome — these are
   recipes the family likes, not a comprehensive index. Filter by cuisine, by category, and by
   free text over the title and ingredients — "French" and "anchovies" and "under an hour" are the kinds
   of question it must answer. Search runs entirely in the browser against a generated index;
   there is no server and no query backend.

3. **A generated JSON index** driving that search — one file covering the whole corpus, with
   each recipe's structured fields: title, slug, category, cuisine, tags, authors, servings,
   total time, and its ingredient lines.

Explicitly **removed** from the current site: the per-category and per-cuisine browse pages, the
category and cuisine index pages, and the Stork search index. Browsing by taxonomy is
pre-processing that generates pages nobody uses; search replaces all of it.

Building the site must parse each recipe into structure — headnote, ingredient groups,
instruction groups, notes — because the templates, the JSON-LD and the search index are all
consumers of that same parse. A group is an optionally named component such as "Walnut Cream"
carrying its own list of lines.

**The corpus moves into this repository and is cleaned once, as it moves.** It is currently
dirty: 27 recipes carry `Category: ToTry`, which is a workflow state and not a category, plus
`Sauces` for `Sauce`, `SideS` for `Sides`, single instances of `Mexican` and `American` used as
categories when they are cuisines, three files with character-encoding damage, and eighteen with
no trailing newline. Fixing the files themselves is preferable to correcting them on every
build: the data should be right where it lives.

Because the data is then clean at rest, the build **validates** rather than normalises. A file
whose category, cuisine or author falls outside the shared vocabulary fails the build and says
which file and which value. That keeps the corpus clean as it grows without silently rewriting
anything.

Deployment: the project lives in a **public GitHub repository** and publishes to **GitHub
Pages** at `recipes.nateemma.com`. Pushing a change builds the site and updates it live, with no
manual step and no other infrastructure.

The markdown files are the only source of truth. The build never modifies them.

---

## Context

### Recommended approach: a small generator, not Pelican

The current site is Pelican 4.8 with a custom theme and three plugins. **Once taxonomy pages
go, Pelican has almost nothing left to do here.** What would still be used: render markdown to
HTML, fill a Jinja template, copy files. What would not: taxonomies, feeds, pagination,
the article/page distinction, translations, drafts, the plugin architecture.

The whole site is 211 recipes, **one** article (`welcome.md`), one search page, and no images.

There is also a specific friction. The parse this project needs — ingredients and instructions
as *structure*, not as rendered HTML — cuts against Pelican's model, which hands templates
`article.content` as one HTML blob. The existing `recipe_reader.py` subclasses `MarkdownReader`
to work around that, and the theme's `base.html` computes relative path prefixes with a repeated
inline conditional in every link, which is a Pelican artifact rather than a real problem.

A direct generator is roughly: read the corpus → parse → render each recipe through a Jinja
template → write `recipes.json` → write the search page. Dependencies: `jinja2`, `markdown`.
That is a few hundred lines that are entirely inspectable, where the parser is the centre of the
program rather than a hook inside a framework.

**When this recommendation would be wrong:** if the site later wants pagination, RSS/Atom feeds,
multiple authors with their own pages, draft support, or a plugin ecosystem. None of those are
in scope, and the corpus is one person's cookbook collection, so they are unlikely.

`/speckit-plan` should treat this as a strong recommendation, not a settled decision, and say so
if it disagrees.

### Where things are

| Thing | Path | Note |
|---|---|---|
| Recipe corpus (source) | `~/Documents/website/recipes-new/content/recipes/` | 211 `.md` files. Moves *into* this repo, cleaned on the way |
| The one article | `~/Documents/website/recipes-new/content/articles/welcome.md` | Not carried over — the search page replaces it |
| Current site | `~/Documents/website/recipes-new/` | Pelican, custom theme, Stork. Reference only |
| Current deploy artifact | `~/Documents/website/recipes/` | A second git repo of built output. Retires entirely — Pages builds from source |
| Markdown grammar contract | `~/code/RecipeScanner/specs/001-scan-cookbook-recipe/contracts/markdown-output.md` | Authoritative |
| Reference parser | `~/code/RecipeScanner/Packages/RecipeKit/Sources/RecipeKit/MarkdownParser.swift` | Swift. Port the grammar, don't reinvent it |
| Shared vocabulary table | `~/code/RecipeScanner/Packages/RecipeKit/Sources/RecipeKit/Generated/vocabulary.json` | Generated. Copy in; regenerate with `make vocab` there |
| Test fixtures | `~/code/RecipeScanner/Packages/RecipeKit/Tests/RecipeKitTests/Fixtures/` | Three sets — see below |

### The migration, in detail

The move is a distinct piece of work with its own acceptance: the corpus arrives clean, and
every change is reviewable as a diff. What has to be fixed:

| Problem | Count | Fix |
|---|---|---|
| `Category: ToTry` | 27 | Not a category. Assign each a real one; keep the marker as a tag if the information is worth keeping |
| `Category: Sauces` | 2 | → `Sauce` |
| `Category: SideS` | 1 | → `Sides` |
| `Category: American` | 1 | `bf_TunaCevichePineapple` — cuisine is already `American`, so the category is simply missing |
| `Category: Mexican` | 1 | `bf_YucatanChickenWraps` — cuisine is already `Southwestern`, category missing |
| `Authors: Ottolenghi` | — | → `Yotam Ottolenghi` |
| Encoding damage (`1Â½`, `â€`) | 3 files | Repair to the intended characters |
| No trailing newline | 18 files | End with exactly one |

**The 27 `ToTry` recipes are all `bf_`** — one book's import where the category was never
assigned. It is a systematic gap, not scattered rot. Their cuisines are already set, so only the
category is missing, and the titles carry most of the answer:

- Obvious `Soup`: Roasted Butternut Squash Soup, Roasted Corn Soup, Crab Gumbo, Trout and Crab
  Soup, White Gazpacho, Cioppino.
- Obvious `Dinner`: Piri-Piri Chicken, Harissa Short Ribs, Lamb Shank with Orzo, Philadelphia
  Strip Steak, Porterhouse Pork Chop, Spanish-Style Steak, Red Curried Lobster, both paellas,
  Mussels in Green Chile Broth, Red Prawns with Gigante Beans.
- Obvious `Sides`: Acorn Squash with Manchego, Charred Corn Parmigiano, Crispy Rice with Black
  Beans.
- **Genuinely ambiguous** — small plates that could be `Appetizer` or `Tapas`, and several are
  Spanish: Queso Fundido, Tuna Tartare, Tequila Cured Salmon, Steamed Baby Clams, Saffron
  Bacalao Crepes, Corn and Wild Rice Pancake, Crisp Potato Pancake with Goat Cheese.

So roughly two thirds infer cleanly and the remainder need a decision, with the
`Appetizer`/`Tapas` boundary being the recurring one. Propose a category per recipe, present the
uncertain ones for confirmation, and do not guess silently — the same human-in-the-loop rule
RecipeScanner works to.

Note that assigning these from the existing 15 categories keeps the extractor's `15 categories`
assertion true. Introducing a new one would not.

Worth deciding separately: `tk_WalnutSoup.md` carries five published OCR errors —
`cut it into & wedges` for `8`, `1 1/s cups` for `1 1/2`, `1 ltbsp sugar` for `1 tbsp`,
`1Â½ cups`, and `walnuts, toosted`. Fixing them is obviously desirable but it is content
editing, not migration.

### Consequences for RecipeScanner

Moving and cleaning the corpus reaches into the other project. Neither is a blocker, but both
should be expected:

- **`make vocab` reads the corpus by path.** Its `--corpus` argument in `RecipeScanner/Makefile`
  points at the old location and will need updating to wherever the corpus lands.
- **The variant maps go empty once the corpus is clean.** `categoryVariants` currently holds
  `Sauces`→`Sauce` and `SideS`→`Sides`; after the fix there is nothing to map. That is correct,
  and the app's `VocabularyMap` still matters for *reading* older files. The excluded set stays —
  it is hard-coded in the extractor, not derived.
- **Category frequency order will shift** when 27 `ToTry` recipes gain real categories, which
  changes the order of the generated Swift enum. Harmless, but it will show up as a diff.
- **The extractor asserts 15 categories and 13 cuisines** and fails loudly otherwise. Assigning
  the `ToTry` recipes from the existing 15 keeps that true; inventing a new category would break
  the build until the expected count is updated.
- **RecipeScanner's test fixtures are already-committed copies** and do not change when the
  corpus does — including `Damage/tk_WalnutSoup.md`, which needs to keep its five errors whatever
  happens to the published file.

### The format, precisely

Front matter is bare `Key: value` lines with **no `---` fences**, in this order: `Title`,
`Summary`, `Date`, `Slug`, `Category`, `Cuisine`, `Tags`, `Authors`, `Total_Time`, `Servings`.
A key is emitted even when empty, with a trailing space. `Date` is `YYYY-MM-DD HH:MM`, no
timezone. Then a blank line, `# Title`, optional headnote prose, `## Ingredients`,
`## Instructions`, and `## Notes` **only when it has content** — 54 of 211 recipes have none.

Component groups are a label line followed by that component's list:

```
## Ingredients

Walnut Cream:

- 1/2 cup walnuts
- 2 cups heavy cream

Pear Puree:

- 1 large pear
```

The same names repeat under `## Instructions`, where ordered numbering restarts at 1 in each
group. One level deep, never nested.

### Things that will bite

- **Vulgar fractions and accents are load-bearing** — `¾`, `1¼`, `½`, `°`, `crème fraîche`,
  `jalapeño`. The corpus also uses U+2044 FRACTION SLASH (`1 1⁄2`), not only `/`.
- **Three corpus files carry encoding damage** — `1Â½` and similar, from UTF-8 read as Latin-1.
  Do not propagate it into JSON-LD or the search index; damaged text is worse when
  machine-readable.
- **`Total_Time` is free text** — `45 minutes`, `3-5 hours`, often empty. `schema.org` wants ISO
  8601 (`PT45M`). Empty is the normal case, not an error. If the search page offers a
  "under an hour" filter, that parse has to be defensive.
- **`schema.org`'s `recipeIngredient` is a flat string array** with nowhere for component
  groups. Decide deliberately how to flatten, and keep the grouped form in `recipes.json`.
- **Some corpus files must not round-trip unchanged.** RecipeScanner splits fixtures three ways:
  `RoundTrip/` (byte-identical), `Normalisation/` (asserts a specific *corrected* output),
  `Damage/` (five real OCR errors published in `tk_WalnutSoup.md`). Reuse that split — a parser
  that round-trips the dirty files perfectly is failing, not passing.
- **Slugs are the filenames** and carry cookbook prefixes (`bf_`, `tk_`, `yo_`, `jc_`, and now
  `mg_`, `in_`, `bi_`). `Slug` always equals the filename without `.md`.

### Search, concretely

211 recipes is small. The whole index fits comfortably in a single JSON file loaded on page
load, filtered in JavaScript — no WASM, no index format, no search library necessarily needed.
Facets worth having: cuisine, category, free text over title and ingredient lines. Sizing the
index and deciding what to include (ingredients certainly; instructions probably; headnote
prose maybe) is a task for the plan.

This index is also, incidentally, what an agent would want for whole-corpus queries — so
`recipes.json` serves both the search page and any later agent use, from one artifact.

### Deploy

**GitHub Pages, public repository, custom domain `recipes.nateemma.com`.**

The workflow is a GitHub Action on push to the default branch: checkout → install dependencies →
build → `actions/upload-pages-artifact` → `actions/deploy-pages`. Nothing else. No AWS account,
no IAM role, no OIDC federation, no ACM certificate, no CloudFront distribution, no bucket
policy, no cache invalidation.

The custom domain needs a `CNAME` DNS record for `recipes.nateemma.com` pointing at
`<username>.github.io`, and the domain entered in the repository's Pages settings. GitHub
provisions and renews the HTTPS certificate automatically.

If the generator emits anything Jekyll would try to process, add a `.nojekyll` file at the site
root — the build output is served as-is.

**This changes the URL shape.** GitHub Pages serves `index.html` for a directory, so clean URLs
are available: `recipes.nateemma.com/BakedRice` rather than `…/BakedRice.html`. The earlier
constraint requiring an explicit `.html` on every link came from the S3 REST endpoint and no
longer applies.

**It also moves the site from a path to a subdomain.** Today the recipes live at
`nateemma.com/recipes/…`, which works because they are a key prefix inside a bucket serving the
whole domain. Pages serves a domain or subdomain, never a path under someone else's, so the site
becomes `recipes.nateemma.com`. The old S3 URLs stop resolving unless redirects are left behind
in the bucket — see the open questions.

Soft limits, noted only for completeness and irrelevant at this size: 1 GB site, 100 GB/month
bandwidth, 10 builds/hour. The current built site is 6 MB.

### Decisions taken (all previously open questions are settled)

`/speckit-clarify` should find little left to ask. Kept here as the record of what was decided
and why.

1. ~~Where does the corpus live?~~ **Settled: `recipes/` at the root of this repository**,
   cleaned as it moves. The old copy under `recipes-new/content/recipes/` is deleted once the
   move is verified.
2. ~~What is serving the live site?~~ **Settled: GitHub Pages**, public repository, custom
   domain `recipes.nateemma.com`. No AWS involvement at all — see the deploy section.
3. ~~Should the old S3 URLs keep working?~~ **Settled: leave the S3 site alone.** It keeps
   running untouched while the new one is built, so both are live in parallel and the old URLs
   go on resolving. Retire it once the new site is working. No redirects needed.
4. ~~What do the 27 `ToTry` recipes become?~~ **Settled: infer the category where the recipe
   makes it obvious, and ask where it does not.** See the note below on how tractable that is.
5. ~~Does `welcome.md` survive?~~ **Settled: no.** The search page becomes the home page and
   carries a short welcome line of its own — something to the effect of "recipes we like" — so
   the article machinery goes entirely.
6. ~~Does the corpus's git history come with it?~~ **Settled: no.** A plain copy into this
   repository is fine; `recipes-new` stays on disk as the archive.
7. ~~Does search need to work without JavaScript?~~ **Settled: JavaScript is fine.** No
   server-rendered fallback listing is required.

### Success looks like

- All 211 recipes render, component groups intact, printable.
- Every recipe page carries valid `schema.org/Recipe` JSON-LD passing Google's Rich Results test.
- The search page finds a recipe by cuisine, by category, and by an ingredient, with no server.
- No published category, cuisine or author value falls outside the shared vocabulary table.
- A push to the default branch updates `recipes.nateemma.com` with no manual step.
- The markdown corpus is untouched by the build.
- The site loads over HTTPS on the custom domain, with a certificate GitHub manages.
