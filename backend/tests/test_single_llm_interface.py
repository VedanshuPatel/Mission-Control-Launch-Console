"""google.genai may be imported only in app/llm/gemini.py."""

from __future__ import annotations

import ast
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1] / "app"
ALLOWED = APP_ROOT / "llm" / "gemini.py"


def _imports_google_genai(path: Path) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "google.genai" or alias.name.startswith("google.genai."):
                    return True
                if alias.name == "google":
                    return True
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if mod == "google.genai" or mod.startswith("google.genai."):
                return True
            if mod == "google" and any(a.name == "genai" for a in node.names):
                return True
    return False


def test_google_genai_imported_only_in_gemini_adapter():
    offenders: list[str] = []
    for path in sorted(APP_ROOT.rglob("*.py")):
        if not _imports_google_genai(path):
            continue
        if path.resolve() != ALLOWED.resolve():
            offenders.append(str(path.relative_to(APP_ROOT.parent)))
    assert offenders == [], "google.genai must only be imported in app/llm/gemini.py:\n" + "\n".join(
        offenders
    )
