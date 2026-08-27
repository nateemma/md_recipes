# Contract: `recipes.json` (provided)

**Provider**: this project's `index.py` | **Consumers**: `search.js`, and any machine reader

One artifact serves both the search page and whole-corpus machine queries (FR-023). It is
public, stable, and served at `https://recipes.nateemma.com/recipes.json`.

## Shape

```json
{
  "generated": "2026-08-26T10:00:00Z",
  "count": 211,
  "categories": ["Appetizer", "Baking", "Basics", "..."],
  "cuisines": ["African", "American", "Asian", "..."],
  "recipes": [
    {
      "slug": "bf_WhiteGazpacho",
      "url": "/bf_WhiteGazpacho",
      "title": "White Gazpacho with Toasted Almond, Champagne Grapes, and Cava",
      "summary": "The other gazpacho",
      "category": "Soup",
      "cuisine": "Spanish",
      "tags": [],
      "authors": ["Bobby Flay"],
      "servings": "4",
      "total_time": "45 minutes",
      "time_min": 45,
      "time_max": 45,
      "ingredients": [
        { "label": null, "items": ["¾ cup slivered almonds, toasted", "2 tablespoons pine nuts, toasted"] }
      ]
    }
  ]
}
```

## Field rules

| Field | Type | Rule |
|---|---|---|
| `generated` | ISO 8601 UTC | Build time. The only non-deterministic value in the file. |
| `count` | int | `len(recipes)`. 211 today. |
| `categories`, `cuisines` | `string[]` | Sorted; exactly the values *in use*, for building the facet controls without a second pass. |
| `slug` | string | Identity. Matches `^[A-Za-z0-9_]+$`. |
| `url` | string | Root-relative, no extension — `/bf_WhiteGazpacho` (FR-038). |
| `title` | string | Verbatim, including `&` and accents. JSON escaping only. |
| `summary` | string \| null | `null` when empty — 19 recipes. |
| `category`, `cuisine` | string | Always present, always in the canonical vocabulary. |
| `tags`, `authors` | `string[]` | Possibly empty. |
| `servings`, `total_time` | string \| null | Free text, verbatim. |
| `time_min`, `time_max` | int \| null | Parsed minutes. Both `null` when unparseable. Equal for a definite time. |
| `ingredients` | `Group[]` | **Grouped form retained** (FR-013). `label` is the display form — no `**`, no trailing `:`. |

## Deliberately excluded

- **Instructions** — roughly triples the file size for a query FR-015 does not scope. Adding them
  later is additive and breaks no consumer.
- **Notes** and **headnote** — same reasoning.
- **Prose lines** inside ingredient groups — a wrapped sentence fragment is not an ingredient, and
  including it would produce false matches on an ingredient search.

## Guarantees to consumers

- Every `slug` in this file has a page at `url`. Every recipe in the corpus is in this file.
- No string contains `U+FFFD`, `Â` or `â€` (FR-024) — the build fails rather than emitting damage.
- Field names and types are stable. New fields may be added; existing ones will not change meaning.
- Size stays well under 500 KB uncompressed at this corpus size.
