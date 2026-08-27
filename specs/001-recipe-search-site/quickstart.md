# Quickstart: Search-First Recipe Site

**Feature**: `001-recipe-search-site` | **Date**: 2026-08-26

Runnable checks that prove the feature works. Each maps to a spec success criterion.

## Prerequisites

- Python 3.11+ (3.12.12 verified on this machine)
- The corpus present at `recipes/` (211 `.md` files), migrated and cleaned
- `data/vocabulary.json` copied from RecipeScanner

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
```

## 1. Migrate the corpus — once

The migration writes to the corpus; nothing else ever does.

```bash
python tools/migrate_corpus.py --dry-run     # prints every change, writes nothing
python tools/migrate_corpus.py               # applies them
git diff --stat recipes/                     # every change reviewable (SC-011)
```

Expected: 211 files created, 53 of them modified — 27 `ToTry` categories, 2 `Sauces`, 1 `SideS`,
2 missing categories, 3 author fixes, 3 encoding repairs, 18 trailing newlines (some files carry
more than one correction).

**Verify the corpus is clean** (SC-005):

```bash
grep -h '^Category:' recipes/*.md | sed 's/^Category: *//' | sort -u | wc -l   # → 15
grep -h '^Cuisine:'  recipes/*.md | sed 's/^Cuisine: *//'  | sort -u | wc -l   # → 13
grep -rl 'ToTry\|Sauces\|SideS' recipes/                                       # → no output
grep -rlE 'Â|â€' recipes/                                                       # → no output
for f in recipes/*.md; do [ -n "$(tail -c 1 "$f")" ] && echo "$f"; done         # → no output
```

## 2. Build

```bash
python -m src.build
```

Expected: exit `0`, under 5 seconds, and

```
build/index.html          the search page
build/recipes.json        211 entries, < 500 KB
build/<Slug>/index.html   211 recipe pages
build/static/             css + js
build/CNAME               recipes.nateemma.com
build/.nojekyll
build/parse-report.md     the label/prose audit — not published
```

```bash
ls build/*/index.html | wc -l                        # → 211  (SC-001)
python -c "import json;d=json.load(open('build/recipes.json'));print(d['count'])"   # → 211
du -h build/recipes.json                             # → well under 500 KB (SC-010)
```

## 3. The corpus is untouched by the build (SC-007, Principle I)

```bash
find recipes -name '*.md' | sort | xargs shasum > /tmp/before
python -m src.build
find recipes -name '*.md' | sort | xargs shasum > /tmp/after
diff /tmp/before /tmp/after && echo "corpus byte-identical"
```

## 4. Validation fails loudly and does not publish (SC-006)

```bash
cp recipes/BakedRice.md /tmp/BakedRice.bak
sed -i '' 's/^Category: .*/Category: Elevenses/' recipes/BakedRice.md
python -m src.build; echo "exit=$?"          # → exit=1, names file and value, writes nothing
cp /tmp/BakedRice.bak recipes/BakedRice.md
```

Repeat with an out-of-vocabulary `Cuisine:` and with `Authors: Ottolenghi` — each must be named,
and **all** violations must appear in one run, not just the first (FR-031).

## 5. Parser correctness — the three fixture sets (Principle VII)

```bash
pytest tests/ -v
pytest tests/test_fixtures.py -v
```

Expected, and the point of the split:

- `RoundTrip/` (5 files) — parse → emit → byte-identical.
- `Normalisation/` (5 files) — emit the **corrected** form. `bf_WhiteGazpacho` gets sequential
  numbering; `BroccoliSalad` gains its trailing newline. **A file that round-trips unchanged here is
  a failure, not a pass.**
- `Damage/` (3 files) — the five published OCR errors in `tk_WalnutSoup` survive untouched.

## 6. Recipe pages render and print (SC-001)

```bash
python -m http.server 8000 --directory build
```

- `http://localhost:8000/tk_WalnutSoup` — three component groups intact in both sections, numbering
  restarting per group.
- `http://localhost:8000/ApricotUpsideDownCake` — no empty Notes heading (one of 54 without notes).
- `http://localhost:8000/bf_WhiteGazpacho` — headnote and italic attribution line present.
- Any page → browser print preview: recipe only, no header, nav or footer (FR-010).
- Check `¾`, `1 1⁄2`, `crème fraîche`, `jalapeño`, `°` render correctly (SC-001, FR-005).

## 7. Search (SC-003, SC-004, SC-013)

At `http://localhost:8000/` — welcome line and full list visible before typing.

| Check | Expect |
|---|---|
| Cuisine → French | Only French recipes; count shown |
| Type `anchovies` | Only recipes with anchovies in title or ingredients |
| Both together | Intersection, not union |
| Type `creme fraiche` (no accents) | Finds `crème fraîche` (FR-021) |
| "under an hour" | `time_max <= 60` only; recipes with no time excluded |
| Nonsense query | Explicit "no matches", not a blank area |
| Clear filters | Full corpus, no reload |
| Copy URL, open in a new tab | Same narrowed results (SC-013) |
| `?cuisine=Klingon` | Full corpus, no error (FR-040) |
| Disconnect network after load, then filter | Still works — no server (FR-018) |

Results should feel instant; DevTools' performance panel should show well under 100 ms per keystroke
(SC-004).

## 8. JSON-LD (SC-002)

```bash
python - <<'PY'
import json,glob,re
for f in sorted(glob.glob('build/*/index.html')):
    m=re.search(r'<script type="application/ld\+json">(.*?)</script>',open(f).read(),re.S)
    assert m, f
    d=json.loads(m.group(1))
    assert d['@type']=='Recipe' and d['name'] and d['recipeIngredient'], f
print('all pages carry valid Recipe JSON-LD')
PY
```

Then, manually, submit three built pages to Google's Rich Results test — one grouped
(`tk_WalnutSoup`), one flat (`BakedRice`), one without `totalTime` (a `3-5 hours` recipe). Zero
errors required.

## 9. Audit the parse (Principle VI)

```bash
less build/parse-report.md
```

408 lines classified as component labels, 89 as prose, 24 whitespace-only discarded. Read once to
confirm no sentence was turned into a heading and no label was demoted to prose.

## 10. Deploy

Push to the default branch and watch the Actions run: checkout → install → build →
upload-pages-artifact → deploy-pages (SC-008).

**Two one-time manual steps, outside the repository:**

1. A `CNAME` DNS record for `recipes.nateemma.com` → `<username>.github.io`.
2. The domain entered in the repository's Settings → Pages, with "Enforce HTTPS" on.

Then `https://recipes.nateemma.com` must load over HTTPS with a valid certificate (SC-009), and the
old S3 site must still be running and untouched (FR-039).

## 11. Cross-project follow-up (SC-014)

```bash
grep -n 'corpus' ~/code/RecipeScanner/Makefile     # must point at this repo's recipes/
cd ~/code/RecipeScanner && make vocab              # must still run
```
