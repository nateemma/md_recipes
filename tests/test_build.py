"""Build-level guarantees, including the one that matters most:
the build never modifies the corpus (Constitution Principle I).
"""

import ast
import hashlib
import subprocess
import sys

import pytest

from src import build

from .conftest import RECIPES, ROOT


def corpus_hashes() -> dict[str, str]:
    return {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(RECIPES.glob("*.md"))
    }


def test_build_does_not_modify_the_corpus(tmp_path):
    """Build twice, hash before and after. The markdown is the source of truth."""
    before = corpus_hashes()
    assert build.main(["--out", str(tmp_path / "b1")]) == build.EXIT_OK
    assert build.main(["--out", str(tmp_path / "b2")]) == build.EXIT_OK
    assert corpus_hashes() == before


def test_build_module_never_imports_the_emitter():
    """The emitter exists only for round-trip tests.

    Principle I forbids anything in the build path from writing markdown, and
    this makes that mechanically enforced rather than merely intended.
    """
    reachable = set()
    to_visit = ["build", "render", "parser", "model", "vocabulary", "timeparse",
                "jsonld", "index", "report"]
    for name in to_visit:
        path = ROOT / "src" / f"{name}.py"
        if not path.exists():
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                reachable.add(node.module.lstrip("."))
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    reachable.add(alias.name)
    assert "emitter" not in reachable, "the build path must not import the emitter"


def test_clean_corpus_exits_zero(tmp_path):
    assert build.main(["--out", str(tmp_path / "out")]) == build.EXIT_OK


def test_bad_category_fails_the_build_and_writes_nothing(tmp_path, capsys):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    source = next(RECIPES.glob("*.md"))
    text = source.read_text(encoding="utf-8").replace(
        "Category: " + build.parse(source.read_text(encoding="utf-8")).category,
        "Category: Elevenses",
        1,
    )
    (corpus / source.name).write_text(text, encoding="utf-8")

    out = tmp_path / "out"
    code = build.main(["--out", str(out), "--corpus", str(corpus)])
    assert code == build.EXIT_VALIDATION
    assert not out.exists(), "no output may be written when validation fails"

    err = capsys.readouterr().err
    assert source.name in err
    assert "Elevenses" in err
    assert "No output written" in err


def test_all_violations_reported_not_only_the_first(tmp_path, capsys):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    for i, source in enumerate(sorted(RECIPES.glob("*.md"))[:3]):
        text = source.read_text(encoding="utf-8")
        text = text.replace("Cuisine: ", "Cuisine: Klingon_", 1)
        (corpus / source.name).write_text(text, encoding="utf-8")

    assert build.main(["--out", str(tmp_path / "o"), "--corpus", str(corpus)]) == (
        build.EXIT_VALIDATION
    )
    err = capsys.readouterr().err
    assert err.count("Cuisine") >= 3
    assert "3 violations in 3 files" in err


def test_unknown_front_matter_key_fails(tmp_path, capsys):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    source = next(RECIPES.glob("*.md"))
    text = source.read_text(encoding="utf-8").replace(
        "Servings:", "Prep_Time: 10 minutes\nServings:", 1
    )
    (corpus / source.name).write_text(text, encoding="utf-8")
    assert build.main(["--out", str(tmp_path / "o"), "--corpus", str(corpus)]) == (
        build.EXIT_VALIDATION
    )
    assert "Prep_Time" in capsys.readouterr().err


def test_encoding_damage_fails_the_build(tmp_path, capsys):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    source = next(RECIPES.glob("*.md"))
    text = source.read_text(encoding="utf-8").replace("# ", "# 1Â½ ", 1)
    (corpus / source.name).write_text(text, encoding="utf-8")
    assert build.main(["--out", str(tmp_path / "o"), "--corpus", str(corpus)]) == (
        build.EXIT_VALIDATION
    )
    assert "Encoding" in capsys.readouterr().err


def test_missing_corpus_is_an_io_error(tmp_path):
    assert build.main(
        ["--out", str(tmp_path / "o"), "--corpus", str(tmp_path / "nope")]
    ) == build.EXIT_IO
