/* Search over the whole corpus, in the browser, against recipes.json.
 *
 * 209 recipes is small. A linear scan with match keys computed once at load is
 * sub-millisecond -- orders of magnitude inside the 100ms budget -- so there is
 * no index format, no WASM and no search library here. */

(function () {
  "use strict";

  var q = document.getElementById("q");
  var cuisine = document.getElementById("cuisine");
  var category = document.getElementById("category");
  var time = document.getElementById("time");
  var clear = document.getElementById("clear");
  var results = document.getElementById("results");
  var count = document.getElementById("count");
  var noMatches = document.getElementById("no-matches");

  if (!q || !results) return;

  var recipes = [];
  var ready = false;

  /* Accent folding, so `creme fraiche` finds `crème fraîche` and `jalapeno`
   * finds `jalapeño`. Typing the accents is not something we should require. */
  function fold(s) {
    return (s || "")
      .toLowerCase()
      .normalize("NFD")
      .replace(/[̀-ͯ]/g, "");
  }

  /* Enough stemming to make plurals work, and no more.
   * "anchovies" must find "anchovy fillets" and "tomatoes" must find "tomato";
   * a real stemmer would be a dependency and a source of surprises for the sake
   * of a 208-recipe cookbook. */
  function stem(w) {
    if (w.length > 3 && /ies$/.test(w)) return w.slice(0, -3) + "y";
    if (w.length > 3 && /(oes|ses|xes|zes|ches|shes)$/.test(w)) return w.slice(0, -2);
    if (w.length > 2 && /s$/.test(w) && !/(ss|us|is)$/.test(w)) return w.slice(0, -1);
    return w;
  }

  /* Search covers the title and the ingredient lines (FR-015). Instructions and
   * notes are deliberately out: they would roughly triple the index for matches
   * a reader looking for "what can I cook with anchovies" does not want. */
  function haystack(r) {
    var parts = [r.title];
    (r.ingredients || []).forEach(function (g) {
      parts = parts.concat(g.items || []);
    });
    var raw = fold(parts.join(" \n "));
    /* Both forms live in the key, so a partial word still matches by substring
     * while a plural or singular matches through the stem. */
    var stemmed = raw.split(/[^a-z0-9]+/).map(stem).join(" ");
    return raw + " \n " + stemmed;
  }

  function matches(r, terms, filters) {
    if (filters.cuisine && r.cuisine !== filters.cuisine) return false;
    if (filters.category && r.category !== filters.category) return false;
    if (filters.time) {
      /* A recipe with no parsed time is excluded rather than treated as zero:
       * "under an hour" should not surface things we cannot vouch for. */
      if (r.time_max === null || r.time_max === undefined) return false;
      if (r.time_max > filters.time) return false;
    }
    for (var i = 0; i < terms.length; i++) {
      if (
        r._key.indexOf(terms[i]) === -1 &&
        r._key.indexOf(stem(terms[i])) === -1
      ) {
        return false;
      }
    }
    return true;
  }

  function render(list) {
    if (!list.length) {
      results.innerHTML = "";
      results.hidden = true;
      noMatches.hidden = false;
    } else {
      var html = "";
      for (var i = 0; i < list.length; i++) {
        var r = list[i];
        html +=
          '<li class="result"><a href="' + r.url + '">' +
          '<span class="result-title">' + escapeHtml(r.title) + "</span>" +
          '<span class="result-meta">' +
          '<span class="pill">' + escapeHtml(r.cuisine) + "</span>" +
          '<span class="pill">' + escapeHtml(r.category) + "</span>" +
          (r.total_time
            ? '<span class="time">' + escapeHtml(r.total_time) + "</span>"
            : "") +
          "</span></a></li>";
      }
      results.innerHTML = html;
      results.hidden = false;
      noMatches.hidden = true;
    }
    count.textContent =
      list.length === 1 ? "1 recipe" : list.length + " recipes";
  }

  function escapeHtml(s) {
    return String(s === null || s === undefined ? "" : s).replace(
      /[&<>"']/g,
      function (c) {
        return {
          "&": "&amp;", "<": "&lt;", ">": "&gt;",
          '"': "&quot;", "'": "&#39;"
        }[c];
      }
    );
  }

  function currentFilters() {
    return {
      cuisine: cuisine.value,
      category: category.value,
      time: time.value ? parseInt(time.value, 10) : null
    };
  }

  function apply() {
    if (!ready) return;
    var terms = fold(q.value).split(/\s+/).filter(Boolean);
    var filters = currentFilters();
    var out = [];
    for (var i = 0; i < recipes.length; i++) {
      if (matches(recipes[i], terms, filters)) out.push(recipes[i]);
    }
    render(out);
  }

  /* --- URL state -----------------------------------------------------------
   * So a narrowed search can be bookmarked or sent to someone. replaceState
   * while typing keeps the back button from stepping through every keystroke;
   * pushState on a discrete filter change makes "back" mean "undo that
   * filter", which is what a reader expects. */

  function writeUrl(push) {
    var p = new URLSearchParams();
    if (q.value.trim()) p.set("q", q.value.trim());
    if (cuisine.value) p.set("cuisine", cuisine.value);
    if (category.value) p.set("category", category.value);
    if (time.value) p.set("time", time.value);
    var url = p.toString() ? "?" + p.toString() : location.pathname;
    try {
      if (push) history.pushState(null, "", url);
      else history.replaceState(null, "", url);
    } catch (e) {
      /* Some browsers refuse history writes on file:// -- search still works. */
    }
  }

  function selectIfPresent(el, value) {
    /* An unrecognised value falls back to "any" rather than erroring or showing
     * nothing, so a stale shared link degrades to the home page. */
    if (!value) { el.value = ""; return; }
    for (var i = 0; i < el.options.length; i++) {
      if (el.options[i].value === value) { el.value = value; return; }
    }
    el.value = "";
  }

  function readUrl() {
    var p = new URLSearchParams(location.search);
    q.value = p.get("q") || "";
    selectIfPresent(cuisine, p.get("cuisine"));
    selectIfPresent(category, p.get("category"));
    selectIfPresent(time, p.get("time"));
  }

  /* --- wiring -------------------------------------------------------------- */

  var pending = null;
  q.addEventListener("input", function () {
    if (pending) cancelAnimationFrame(pending);
    pending = requestAnimationFrame(function () {
      apply();
      writeUrl(false);
    });
  });

  [cuisine, category, time].forEach(function (el) {
    el.addEventListener("change", function () {
      apply();
      writeUrl(true);
    });
  });

  clear.addEventListener("click", function () {
    q.value = "";
    cuisine.value = "";
    category.value = "";
    time.value = "";
    apply();
    writeUrl(true);
  });

  window.addEventListener("popstate", function () {
    readUrl();
    apply();
  });

  fetch("/recipes.json")
    .then(function (r) { return r.json(); })
    .then(function (data) {
      recipes = data.recipes || [];
      for (var i = 0; i < recipes.length; i++) {
        recipes[i]._key = haystack(recipes[i]);
      }
      ready = true;
      readUrl();
      apply();
    })
    .catch(function () {
      /* The server-rendered list is already on the page, so a failed fetch
       * leaves a browsable site rather than an empty one. */
      count.textContent += " (search unavailable)";
    });
})();
