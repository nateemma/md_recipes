# Contract: `schema.org/Recipe` JSON-LD (provided)

**Provider**: this project's `jsonld.py` | **Consumers**: crawlers, assistants, Google Rich Results

One `<script type="application/ld+json">` per recipe page, so a machine gets the recipe without
parsing HTML (FR-011).

## Mapping

| JSON-LD | Source | Rule |
|---|---|---|
| `@context` | — | `"https://schema.org"` |
| `@type` | — | `"Recipe"` |
| `name` | `title` | Verbatim. |
| `description` | `summary` | Omitted when empty. |
| `datePublished` | `date` | `YYYY-MM-DD`. Omitted when absent. |
| `recipeCategory` | `category` | Canonical value. |
| `recipeCuisine` | `cuisine` | Canonical value. |
| `keywords` | `tags` | Comma-joined. Omitted when empty. |
| `author` | `authors` | `{"@type": "Person", "name": …}` per author. |
| `recipeYield` | `servings` | Free text — `4`, `4-6`. Omitted when absent. |
| `totalTime` | `total_time` | ISO 8601. **Only when the parse is definite** (FR-012). |
| `recipeIngredient` | `ingredients` | **Flat**, source order, group names dropped. |
| `recipeInstructions` | `instructions` | `HowToSection` when grouped, else `HowToStep[]`. |
| `url` | `slug` | Absolute — `https://recipes.nateemma.com/<Slug>`. |

## `recipeIngredient` — flattening

Settled by clarification (spec Clarifications, FR-013). Every ingredient line appears **exactly
once**, as a clean string, in source order. Group names are **omitted**. Prose lines are excluded.

```json
"recipeIngredient": ["1/2 cup walnuts", "2 cups heavy cream", "1 large pear"]
```

Not `"Walnut Cream: 1/2 cup walnuts"` — a consumer rendering the string verbatim would show a
compound that is not an ingredient. Not `"Walnut Cream:"` as its own entry — that puts a
non-ingredient into an array of ingredients, breaking any consumer that counts items or builds a
shopping list. The grouping is not lost: it is on the page and in `recipes.json`.

## `recipeInstructions` — grouping is kept

`schema.org` *does* model instruction grouping, so it is used where the vocabulary supports it.

Grouped (74 recipes):

```json
"recipeInstructions": [
  { "@type": "HowToSection", "name": "Walnut Cream",
    "itemListElement": [
      { "@type": "HowToStep", "text": "Place the walnuts, cream, and milk in a saucepan." }
    ] }
]
```

Ungrouped: a flat `HowToStep[]`.

Prose lines are excluded from steps for the same reason they are excluded from ingredients — a
wrapped fragment is not a step.

## `totalTime` — omitted when uncertain

Emitted only when the parse yields a single definite duration (207 of 211). Ranges (`3-5 hours`) and
`overnight` are omitted rather than guessed, because `totalTime` is a single `Duration` with nowhere
to express uncertainty. A Recipe with no `totalTime` is still valid (FR-012).

## Validation

Every page must pass Google's Rich Results test as a Recipe with zero errors (SC-002). `test_jsonld.py`
asserts the required fields and that the JSON parses; the Rich Results check is a manual step in
`quickstart.md` against a sample.
