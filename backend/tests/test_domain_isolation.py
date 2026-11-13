"""Prove domain verdicts cannot come from a model: no LLM/pipeline imports."""

from __future__ import annotations

import ast
from pathlib import Path

FORBIDDEN_PREFIXES = ("app.llm", "app.pipeline", "google.genai")
APP_ROOT = Path(__file__).resolve().parents[1] / "app"


def _resolve_from_import(path: Path, node: ast.ImportFrom) -> str | None:
    """Return absolute module name for absolute or relative ImportFrom."""
    if node.level == 0:
        return node.module

    # Relative: climb from the importing file's package directory.
    package_dir = path.parent
    for _ in range(node.level - 1):
        package_dir = package_dir.parent

    try:
        rel = package_dir.relative_to(APP_ROOT)
    except ValueError:
        return node.module

    base_parts = ("app", *rel.parts)
    if node.module:
        return ".".join((*base_parts, *node.module.split(".")))
    return ".".join(base_parts)


def _imported_modules(path: Path, tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            resolved = _resolve_from_import(path, node)
            if resolved:
                names.add(resolved)
    return names


def test_domain_package_imports_nothing_from_llm_or_pipeline():
    domain_root = APP_ROOT / "domain"
    assert domain_root.is_dir(), "app/domain/ must exist"
    py_files = sorted(domain_root.rglob("*.py"))
    assert py_files, "app/domain/ must contain Python modules"

    offenders: list[str] = []
    for path in py_files:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for name in _imported_modules(path, tree):
            if any(name == p or name.startswith(p + ".") for p in FORBIDDEN_PREFIXES):
                offenders.append(f"{path.relative_to(APP_ROOT.parent)}: {name}")

    assert offenders == [], "domain must not import LLM/pipeline modules:\n" + "\n".join(
        offenders
    )
