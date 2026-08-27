# Feature Specification: Search-First Recipe Site

**Feature Branch**: `001-recipe-search-site`

**Created**: 2026-08-26

**Status**: Draft

**Input**: User description: "Build a static site for the Price Family Recipes collection, generated from a directory of markdown recipe files, where search is the only navigation and publishing is automatic."

## Clarifications

### Session 2026-08-26

- Q: Seven of the 27 `ToTry` recipes are small plates where Appetizer and Tapas are both
  defensible. Which rule should the migration apply? → A: All seven become `Appetizer`. `Tapas`
  is left at its single existing recipe.
- Q: Deleting the old corpus location breaks `make vocab` in the RecipeScanner repository, whose
  Makefile points `--corpus` at the old path. Should fixing that be part of this feature? → A:
  Yes — update the path. Do not regenerate the vocabulary table as part of this work.
- Q: `schema.org`'s `recipeIngredient` is a flat string array with nowhere for component group
  names. How should grouped ingredients be flattened into it? → A: Flat, in source order, group
  names dropped. Grouping is preserved on the page and in the index.
- Q: Should search state live in the URL so a narrowed search can be bookmarked or shared? → A:
  Yes — query and filters are reflected in the URL.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Read a recipe while cooking (Priority: P1)

A family member has landed on a recipe — from a bookmark, a shared link, or a search result — and
needs to cook from it. They see the title, a short headnote if the recipe has one, the ingredients
grouped by component ("Walnut Cream", "Pear Puree") in the order the cookbook gave them, the
instructions with numbering that restarts inside each component, and any notes. They can print the
page and get a clean sheet with no site furniture on it.

**Why this priority**: The recipes are the product. A site that only searches but renders recipes
badly is worthless; a site that renders recipes well and has no search is still a usable cookbook.
This story alone is a shippable cookbook.

**Independent Test**: Build the site from the corpus and open any recipe page directly. It renders
title, headnote, grouped ingredients, grouped instructions and notes, and prints legibly — with no
search page and no index file present.

**Acceptance Scenarios**:

1. **Given** a recipe whose ingredients are split into named components, **When** the reader opens
   its page, **Then** each component name appears as a heading above only its own ingredient lines,
   in the order the source file lists them.
2. **Given** a recipe whose instructions restart numbering inside each component, **When** the
   reader opens its page, **Then** each component's steps are numbered from 1.
3. **Given** a recipe with no `## Notes` section (54 of 211 have none), **When** the reader opens
   its page, **Then** no empty Notes heading is shown.
4. **Given** any recipe page, **When** the reader prints it, **Then** the printed sheet contains the
   recipe content and omits navigation, search controls and footer chrome.
5. **Given** a recipe containing vulgar fractions, fraction slashes and accented characters
   (`¾`, `1 1⁄2`, `crème fraîche`, `jalapeño`), **When** the reader opens its page, **Then** those
   characters display exactly as the source file holds them, with no mojibake and no substitution.

---

### User Story 2 - Find a recipe by what you have or what you fancy (Priority: P1)

Someone arrives at the home page. A line or two of welcome tells them these are recipes the family
likes, not a comprehensive index. From there the only navigation is search: they narrow by cuisine,
narrow by category, and type free text that matches recipe titles and ingredient lines. "French",
"anchovies", and "something under an hour" are all answerable. Results appear as they type, with no
page reload and no request to any server, and clicking a result opens the recipe.

**Why this priority**: Search is the site's entire navigation model — every browse page is being
deleted in favour of it. Without this the corpus is 211 unreachable pages.

**Independent Test**: Open the home page with the network disconnected after first load, filter by
cuisine, by category, and by an ingredient word, and confirm each returns the expected recipes and
that every result links to a page that exists.

**Acceptance Scenarios**:

1. **Given** the home page has loaded, **When** the reader selects cuisine "French", **Then** only
   recipes whose cuisine is French are listed, and the count of matches is visible.
2. **Given** the home page has loaded, **When** the reader types "anchovies", **Then** recipes whose
   title or any ingredient line contains that word are listed, and recipes that do not are excluded.
3. **Given** a cuisine filter and a text query are both active, **When** results are shown, **Then**
   only recipes satisfying both are listed.
4. **Given** filters are active, **When** the reader clears them, **Then** the full corpus is listed
   again without a page reload.
5. **Given** a query matches nothing, **When** results are shown, **Then** an explicit "no matches"
   message is shown rather than a blank area.
6. **Given** the reader wants a quick recipe, **When** they apply the "under an hour" time filter,
   **Then** recipes whose stated total time is an hour or less are listed, and recipes with no
   stated time are excluded from that filtered set rather than treated as zero.
7. **Given** the home page, **When** it first renders, **Then** the welcome line and the full recipe
   list are present without the reader having typed anything.
8. **Given** the reader has narrowed to French recipes containing anchovies, **When** they copy the
   address and open it elsewhere, **Then** the same narrowed result set is shown.

---

### User Story 3 - A machine reads the corpus (Priority: P2)

A crawler, an assistant, or a future tool wants the recipes as data rather than as pages. Each
recipe page carries `schema.org/Recipe` structured data covering its name, ingredients, steps,
yield, time, category, cuisine and author, so a crawler gets the recipe without parsing the page's
markup. Separately, one generated index file describes the whole corpus in one request, so a tool
answering "which recipes use anchovies" reads one artifact instead of 211 pages.

**Why this priority**: It is what makes the site legible beyond the family, and the index is
required by Story 2 anyway — this story is mostly the discipline of making that same artifact good
enough to be a public interface.

**Independent Test**: Feed a sample of built recipe pages to a structured-data validator and confirm
they pass; fetch the index file alone and answer a whole-corpus question from it with no other file.

**Acceptance Scenarios**:

1. **Given** any built recipe page, **When** it is submitted to a structured-data validator,
   **Then** it reports a valid Recipe with no errors.
2. **Given** a recipe with component groups, **When** its structured data is read, **Then** every
   ingredient line in the recipe appears in the ingredient list, and the component each line belongs
   to is not lost from the page itself.
3. **Given** a recipe whose total time is stated in free text such as "45 minutes", **When** its
   structured data is read, **Then** the time is expressed in the standard machine format.
4. **Given** a recipe whose total time is empty (the common case), **When** its structured data is
   read, **Then** the time field is simply absent and the recipe is still valid.
5. **Given** the index file, **When** it is read on its own, **Then** it contains, for every recipe
   in the corpus, the title, slug, category, cuisine, tags, authors, servings, total time and
   ingredient lines.

---

### User Story 4 - The corpus arrives clean and stays clean (Priority: P1)

The 211 markdown files move into this repository once, and the known defects are fixed in the files
themselves as part of that move — the 27 recipes marked with a workflow state instead of a category,
the misspelled category values, the two files where a cuisine was written in the category field, the
three files with character-encoding damage, the eighteen missing a trailing newline, and the author
recorded by surname only. Every change is reviewable as a diff. Afterwards the build validates and
never rewrites: a file whose category, cuisine or author is outside the shared vocabulary fails the
build with the offending file and value named.

**Why this priority**: Stories 1-3 all consume the same parse of the same files. Dirty data
published as machine-readable data is worse than dirty data on a page, and the alternative — patching
values on every build — hides the defect forever.

**Independent Test**: Run the build against the migrated corpus and confirm it succeeds; introduce a
file with an out-of-vocabulary category and confirm the build fails naming that file and value; run
the build twice and confirm no source file's bytes changed.

**Acceptance Scenarios**:

1. **Given** the migrated corpus, **When** every file's category is checked, **Then** none carries
   the workflow-state value, none carries a misspelled variant, and none carries a cuisine name.
2. **Given** the migrated corpus, **When** the set of distinct categories is compared with the shared
   vocabulary, **Then** no new category has been introduced by the migration and the count of
   distinct categories is still 15.
3. **Given** the 27 recipes that carried the workflow state, **When** their categories are read
   after migration, **Then** six are `Soup`, eleven are `Dinner`, three are `Sides` and seven are
   `Appetizer`, and none is `Tapas`.
4. **Given** a recipe file whose category, cuisine or author is not in the shared vocabulary,
   **When** the site is built, **Then** the build fails, names the file and the offending value, and
   writes no output.
5. **Given** the corpus, **When** the site is built, **Then** the markdown files are byte-identical
   before and after.
6. **Given** the three files with encoding damage, **When** they are read after migration, **Then**
   they contain the intended characters, and no damaged text reaches any page or the index.
7. **Given** every migrated file, **When** its last byte is checked, **Then** the file ends with
   exactly one newline.

---

### User Story 5 - Publishing is a push (Priority: P2)

A recipe is added, edited, or fixed. The author pushes to the default branch and the live site at
the custom domain updates on its own — no build run by hand, no upload step, no second repository of
built output to keep in sync. If the push contains a file that fails validation, the deployment does
not happen and the failure is visible.

**Why this priority**: It removes the manual publish step and the separate deploy repository, but the
site is testable and usable before it is automated.

**Independent Test**: Push a change to the default branch and observe the live site reflect it with
no further action; push a deliberately invalid file and observe the deployment refuse to publish.

**Acceptance Scenarios**:

1. **Given** a change pushed to the default branch, **When** the pipeline finishes, **Then** the live
   site serves the change with no manual step.
2. **Given** a push containing a file that fails vocabulary validation, **When** the pipeline runs,
   **Then** it fails, the live site is unchanged, and the failure names the file and value.
3. **Given** the live site, **When** it is loaded at the custom domain, **Then** it is served over
   HTTPS with a valid certificate.
4. **Given** any recipe's address, **When** it is opened, **Then** it resolves without a file
   extension in the URL.

---

### Edge Cases

- A recipe with no component groups at all — the common case — renders as one plain ingredient list
  and one plain numbered instruction list, with no empty group heading.
- A recipe whose ingredients are grouped but whose instructions are not, or the reverse.
- A recipe with an empty front-matter value (a key present with nothing after it) — normal, not an
  error; the field is simply absent from the page and the index.
- Total time in a form that is not a plain duration (`3-5 hours`, `overnight`, empty). Time parsing
  must never fail the build and never guess; unparseable means "no time known".
- A recipe title, category or cuisine containing characters that need escaping in a page or in the
  index file.
- Two recipes whose titles are identical — the file name, not the title, identifies a recipe.
- A recipe with a headnote but no notes, and a recipe with notes but no headnote.
- The reader's browser blocks scripts: the site's search does not work, which is accepted; recipe
  pages themselves remain fully readable without scripts.
- A search query with mixed case, accented characters, or a fraction character in it.
- A shared search URL naming a cuisine or category that no longer exists — the reader sees the full
  corpus, not an error and not an empty page.
- The index grows as recipes are added; the home page must stay usable as the corpus grows well
  beyond its current size.

## Requirements *(mandatory)*

### Functional Requirements

**Source format and parsing**

- **FR-001**: The system MUST read recipes from markdown files whose front matter is bare
  `Key: value` lines with no fence delimiters, followed by a title heading, an optional headnote, an
  ingredients section, an instructions section, and an optional notes section.
- **FR-002**: The system MUST treat that file format as fixed and MUST NOT change it, because it is
  the output contract of a separate application that has byte-level tests against the same corpus.
- **FR-003**: The system MUST parse each recipe into structure — front-matter fields, headnote,
  ingredient groups, instruction groups, notes — and MUST use that single parse as the source for the
  recipe pages, the structured data and the search index.
- **FR-004**: The system MUST represent an ingredient or instruction group as an optionally named
  component carrying its own ordered lines, one level deep and never nested, preserving source order.
- **FR-005**: The system MUST preserve the source's characters exactly — vulgar fractions, fraction
  slashes, degree signs and accented letters — through every output.
- **FR-006**: The system MUST identify each recipe by its file name without extension, and MUST
  require that the recipe's declared slug equals that name.
- **FR-007**: The system MUST NOT modify, rewrite or reformat any source markdown file at build time.

**Recipe pages**

- **FR-008**: The system MUST generate one page per recipe showing title, headnote when present,
  ingredient groups, instruction groups and notes when present, with group names shown as headings
  and instruction numbering restarting within each group.
- **FR-009**: The system MUST omit a section entirely when the recipe has no content for it, rather
  than rendering an empty heading.
- **FR-010**: Recipe pages MUST print legibly, omitting navigation and other site chrome from the
  printed output.
- **FR-011**: Each recipe page MUST carry `schema.org/Recipe` structured data covering name,
  ingredients, instructions, and the recipe's category, cuisine, author, yield and time where those
  are present.
- **FR-012**: The system MUST express total time in the standard machine format in structured data
  when the source's free-text time can be understood, and MUST omit the field otherwise rather than
  guessing or failing.
- **FR-013**: The system MUST flatten grouped ingredients into the structured-data ingredient list
  as one clean string per ingredient line, in source order, with component group names omitted.
  Every ingredient line MUST appear exactly once, no entry in that list may be anything other than
  an ingredient, and the grouped form MUST be retained on the recipe page and in the search index.

**Search page**

- **FR-014**: The home page MUST be the search page, MUST open with a short welcome establishing that
  these are recipes the family likes rather than a comprehensive index, and MUST list the corpus
  before any query is entered.
- **FR-015**: The search page MUST offer filtering by cuisine, by category, and by free text matched
  against recipe titles and ingredient lines.
- **FR-016**: The search page MUST offer a total-time filter answering "under an hour", excluding
  recipes with no stated time from that filtered set.
- **FR-017**: Filters MUST combine, narrowing results to recipes satisfying all active filters.
- **FR-018**: Search MUST run entirely in the reader's browser against the generated index, with no
  server-side query component and no request per keystroke.
- **FR-019**: The search page MUST show the number of matching recipes and MUST show an explicit
  message when nothing matches.
- **FR-020**: Each result MUST link to that recipe's page.
- **FR-021**: Free-text matching MUST be case-insensitive and MUST match accented text sensibly, so
  that a query typed without accents still finds accented content.
- **FR-040**: The active free-text query and filter selections MUST be reflected in the page's URL,
  so that a narrowed search can be bookmarked and shared, and the browser's back and forward
  controls move between previous searches. Opening such a URL MUST restore that search. A URL
  carrying an unrecognised filter value MUST fall back to showing the unfiltered corpus rather than
  erroring or showing nothing.

**Generated index**

- **FR-022**: The system MUST generate one index file covering the whole corpus, containing for each
  recipe its title, slug, category, cuisine, tags, authors, servings, total time and ingredient
  lines.
- **FR-023**: The index MUST be usable on its own as a description of the corpus, serving both the
  search page and any later machine consumer, from a single artifact.
- **FR-024**: The index MUST contain no character-encoding damage.

**Corpus migration and validation**

- **FR-025**: The corpus MUST be copied into this repository once and cleaned as part of that move,
  with every correction reviewable as a diff.
- **FR-026**: Migration MUST replace the workflow-state category on the 27 affected recipes with a
  real category drawn from the existing vocabulary and MUST NOT introduce a new category. The
  assignment is: `Soup` for the six soups and stews, `Dinner` for the eleven main courses, `Sides`
  for the three side dishes, and `Appetizer` for the seven small plates. The resulting per-recipe
  assignment MUST be presented for review as a diff before it is applied.
- **FR-026a**: Migration MUST NOT assign any recipe to `Tapas`; that category retains its single
  existing recipe. The count of distinct categories MUST remain 15 after migration.
- **FR-027**: Migration MUST correct the misspelled category values, MUST supply the missing category
  on the two files whose category field holds a cuisine name, and MUST record the author known by
  surname under the full name used by the shared vocabulary.
- **FR-028**: Migration MUST repair the three files carrying character-encoding damage to the
  intended characters.
- **FR-029**: Migration MUST ensure every file ends with exactly one newline.
- **FR-030**: The build MUST validate rather than normalise: every category, cuisine and author value
  MUST be checked against the shared vocabulary, and a value outside it MUST fail the build naming
  the file and the value, with no output written.
- **FR-031**: Validation MUST report all offending files and values in one run rather than stopping
  at the first.

**Scope removals**

- **FR-032**: The system MUST NOT generate per-category or per-cuisine browse pages, category or
  cuisine index pages, or a separate search-engine index artifact; search replaces all taxonomy
  browsing.
- **FR-033**: The site MUST consist only of recipe pages, the search home page, and the generated
  index, plus the static assets those require.
- **FR-034**: The existing welcome article MUST NOT be carried over; its role passes to the welcome
  line on the search page.

**Publishing**

- **FR-035**: The project MUST live in a public repository and MUST publish automatically on push to
  the default branch, with no manual build or upload step and no second repository of built output.
- **FR-036**: A push whose content fails validation MUST NOT publish, and the failure MUST be
  visible.
- **FR-037**: The site MUST be served over HTTPS at the custom domain with a certificate renewed
  without manual intervention.
- **FR-038**: Recipe addresses MUST NOT require a file extension.
- **FR-039**: The previously published site MUST be left running and untouched while this one is
  built, so existing addresses keep resolving until it is retired deliberately.

**Cross-project consequences**

- **FR-041**: Because the corpus moves, the separate recipe-scanning project's vocabulary-generation
  step — which locates the corpus by path — MUST be updated to the new location as part of this
  work, so that no sibling project is left pointing at a deleted directory.
- **FR-042**: This work MUST NOT regenerate the shared vocabulary table. The table is copied in as
  it stands; regenerating it remains the other project's decision, to be taken deliberately when it
  wants the reordering and empty variant maps that a clean corpus produces.

### Key Entities

- **Recipe**: One markdown file and everything parsed from it — identity (slug, equal to the file
  name), title, summary, date, category, cuisine, tags, authors, servings, total time, headnote,
  ingredient groups, instruction groups, notes. The single unit the pages, structured data and index
  all describe.
- **Component group**: An optionally named part of a recipe ("Walnut Cream") holding an ordered list
  of lines. Appears under both ingredients and instructions, where the same names recur. Never
  nested. A recipe with no named components has exactly one unnamed group.
- **Vocabulary**: The shared, externally generated table of permitted categories, cuisines and
  authors. The build's validation authority; owned by the other project and copied in.
- **Search index**: The single generated artifact describing every recipe's structured fields and
  ingredient lines. Consumed by the search page and by any machine reader.
- **Migration record**: The one-time set of corrections applied to the corpus as it moves — what was
  changed in which file and why — reviewable as a diff.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All 211 recipes render, with component groups intact and instruction numbering
  restarting per group, and every one prints as a clean sheet.
- **SC-002**: Every recipe page passes a structured-data validator as a Recipe with zero errors.
- **SC-003**: A reader can find a recipe by cuisine, by category, and by an ingredient word, with no
  server involved, and each of those returns the correct set with no false negatives.
- **SC-004**: Results update within a keystroke's worth of delay — under 100ms — for the whole corpus
  on a typical laptop, and the home page becomes usable within 2 seconds on a normal connection.
- **SC-005**: No published category, cuisine or author value falls outside the shared vocabulary, and
  the count of distinct categories is unchanged by the migration.
- **SC-006**: A file with an out-of-vocabulary value fails the build, and the message identifies the
  file and the value precisely enough to fix it without further searching.
- **SC-007**: The markdown corpus is byte-identical before and after any number of builds.
- **SC-008**: A push to the default branch updates the live site with zero manual steps.
- **SC-009**: The live site loads over HTTPS at the custom domain with a valid certificate.
- **SC-010**: The whole corpus is described by one index file, small enough to load on page open
  without a perceptible wait.
- **SC-011**: Every migration change is visible as a reviewable diff, and no ambiguous category was
  assigned without human confirmation.
- **SC-012**: The generated site contains no taxonomy browse or index pages.
- **SC-013**: A narrowed search can be shared as a link that reproduces the same results for the
  recipient.
- **SC-014**: No sibling project is left referring to the corpus's old location after the move.

## Assumptions

- The shared vocabulary table is owned and generated by the separate recipe-scanning project and is
  copied into this repository as it currently stands; regenerating it remains that project's
  responsibility and is explicitly not done here.
- Assigning all seven ambiguous small plates to `Appetizer` leaves `Tapas` holding one recipe. That
  is accepted: `Tapas` is a real vocabulary value and a rarely-used facet, not a defect.
- The markdown grammar contract and its reference parser in that project are authoritative; this
  project ports the grammar rather than inventing one.
- That project's three-way fixture split — files that must round-trip byte-identically, files that
  must produce a specific corrected output, and files carrying real published errors that must be
  preserved — is the correct model of expected parser behaviour and is reused here.
- The published OCR errors inside one recipe's text are content editing, not migration, and are out
  of scope for this feature.
- The 27 workflow-state recipes are one book import with a systematic gap; their cuisines are already
  correct, so only the category is missing.
- Search requires JavaScript; no server-rendered fallback listing is required, and this is accepted.
- The corpus has no images, and none are in scope.
- The corpus's version history does not move with it; the previous location remains on disk as the
  archive.
- The corpus is roughly 200-300 recipes and grows slowly; the whole index loading at once is
  appropriate at this size and for a comfortable multiple of it.
- Readers are family and their friends on modern browsers; there is no login, no personalisation and
  no user-generated content.
- Time filtering is best-effort over free text: empty is the normal case, not an error.
