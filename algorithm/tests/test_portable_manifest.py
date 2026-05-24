"""Checks for the portable-core copy manifest."""

from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
START = "<!-- portable-core-files:start -->"
END = "<!-- portable-core-files:end -->"
BANNED_INTERNAL_MODULES = {"cases", "layout_fixtures", "viz"}


def _portable_files() -> list[Path]:
    text = (ROOT / "PORTABLE_CORE.md").read_text()
    block = text.split(START, 1)[1].split(END, 1)[0]
    rels = [
        line.strip()
        for line in block.splitlines()
        if line.strip().startswith("celllayout_tf/")
    ]
    return [ROOT / rel for rel in rels]


def test_portable_manifest_files_exist_and_exclude_testfield_modules():
    files = _portable_files()
    assert files, "portable manifest should list package files"

    rels = {f.relative_to(ROOT).as_posix() for f in files}
    assert "celllayout_tf/__init__.py" in rels
    assert "celllayout_tf/api.py" in rels
    assert "celllayout_tf/cases.py" not in rels
    assert "celllayout_tf/layout_fixtures.py" not in rels
    assert "celllayout_tf/viz.py" not in rels

    missing = [f for f in files if not f.exists()]
    assert not missing


def test_portable_files_do_not_import_testfield_modules():
    offenders: list[str] = []
    for path in _portable_files():
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if node.level == 1 and module.split(".")[0] in BANNED_INTERNAL_MODULES:
                    offenders.append(f"{path.relative_to(ROOT)} imports .{module}")
                if module.startswith("celllayout_tf."):
                    name = module.split(".", 1)[1].split(".")[0]
                    if name in BANNED_INTERNAL_MODULES:
                        offenders.append(f"{path.relative_to(ROOT)} imports {module}")
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("celllayout_tf."):
                        name = alias.name.split(".", 1)[1].split(".")[0]
                        if name in BANNED_INTERNAL_MODULES:
                            offenders.append(
                                f"{path.relative_to(ROOT)} imports {alias.name}"
                            )
    assert offenders == []
