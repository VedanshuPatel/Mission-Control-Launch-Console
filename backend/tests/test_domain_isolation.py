"""Prove domain verdicts cannot come from a model: no LLM/pipeline imports."""

from __future__ import annotations

import ast
from pathlib import Path

FORBIDDEN_PREFIXES = ("app.llm", "app.pipeline", "google.genai")


def _imported_modules(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def test_domain_package_imports_nothing_from_llm_or_pipeline():
    domain_root = Path(__file__).resolve().parents[1] / "app" / "domain"
    assert domain_root.is_dir(), "app/domain/ must exist"
    py_files = sorted(domain_root.rglob("*.py"))
    assert py_files, "app/domain/ must contain Python modules"

    offenders: list[str] = []
    for path in py_files:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for name in _imported_modules(tree):
            if any(name == p or name.startswith(p + ".") for p in FORBIDDEN_PREFIXES):
                offenders.append(f"{path.relative_to(domain_root.parent.parent)}: {name}")

    assert offenders == [], "domain must not import LLM/pipeline modules:\n" + "\n".join(
        offenders
    )
