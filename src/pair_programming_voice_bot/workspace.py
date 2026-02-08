"""Workspace-level file tools."""

from __future__ import annotations

from pathlib import Path
from typing import List


class WorkspaceError(ValueError):
    pass


class QuestionWorkspace:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()

    def _resolve(self, relative_path: str) -> Path:
        path = (self.root / relative_path).resolve()
        if path != self.root and self.root not in path.parents:
            raise WorkspaceError(f"Path escapes workspace: {relative_path}")
        return path

    def list_files(self) -> List[str]:
        files: List[str] = []
        for path in self.root.rglob("*"):
            if path.is_file():
                files.append(path.relative_to(self.root).as_posix())
        return sorted(files)

    def read_file(self, path: str) -> str:
        target = self._resolve(path)
        if not target.exists():
            raise WorkspaceError(f"File not found: {path}")
        return target.read_text(encoding="utf-8")

    def read_description(self, level: int = 1) -> str:
        if level <= 1:
            filename = "desc.md"
        else:
            filename = f"desc_level{level}.md"
        return self.read_file(filename)

    def get_current_code(self, file_path: str = "ruleengine.py") -> str:
        return self.read_file(file_path)

    def apply_patch(self, file_path: str, old_text: str, new_text: str) -> str:
        target = self._resolve(file_path)
        if not target.exists():
            raise WorkspaceError(f"File not found: {file_path}")
        content = target.read_text(encoding="utf-8")
        matches = content.count(old_text)
        if matches != 1:
            raise WorkspaceError(
                f"Patch requires exactly one match in {file_path}, found {matches}."
            )
        updated = content.replace(old_text, new_text, 1)
        target.write_text(updated, encoding="utf-8")
        return f"Patched {file_path}."

