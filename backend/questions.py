import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .config import QUESTIONS_ROOT


@dataclass
class Stage:
    name: str
    visible_tests: List[str]
    hidden_tests: List[str]
    reveal_files: List[str] = None  # files to reveal when this stage unlocks

    @classmethod
    def from_json(cls, data: Dict) -> "Stage":
        return cls(
            name=data.get("name", "Stage"),
            visible_tests=data.get("visible_tests", []),
            hidden_tests=data.get("hidden_tests", []),
            reveal_files=data.get("reveal_files", []),
        )


@dataclass
class QuestionConfig:
    name: str
    visible_files: List[str]
    entrypoint: str
    environment: Dict[str, str]
    default_duration_minutes: int
    stages: List[Stage]
    tags: Optional[List[str]] = None
    estimated_difficulty: Optional[str] = None

    @classmethod
    def from_json(cls, data: Dict) -> "QuestionConfig":
        stages_raw = data.get("stages")
        stages = []
        if stages_raw:
            stages = [Stage.from_json(s) for s in stages_raw]
        return cls(
            name=data["name"],
            visible_files=data["visible_files"],
            entrypoint=data["entrypoint"],
            environment=data.get("environment", {}),
            default_duration_minutes=data.get("default_duration_minutes", 60),
            stages=stages,
            tags=data.get("tags"),
            estimated_difficulty=data.get("estimated_difficulty"),
        )


def question_root(question_name: str) -> Path:
    return QUESTIONS_ROOT / question_name


def load_question_config(question_name: str) -> QuestionConfig:
    cfg_path = question_root(question_name) / "question.json"
    if not cfg_path.exists():
        raise FileNotFoundError(f"Question {question_name} not found")
    with cfg_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    cfg = QuestionConfig.from_json(data)
    if not cfg.stages:
        cfg.stages = [
            Stage(
                name="Stage 1",
                visible_tests=[cfg.entrypoint],
                hidden_tests=[p.name for p in get_hidden_files(question_name)],
            )
        ]
    return cfg


def load_visible_files(question_name: str, cfg: QuestionConfig) -> Dict[str, str]:
    root = question_root(question_name)
    files: Dict[str, str] = {}
    # Always include desc.md
    desc_path = root / "desc.md"
    if desc_path.exists():
        files["desc.md"] = desc_path.read_text(encoding="utf-8")

    for rel_path in cfg.visible_files:
        path = root / rel_path
        if not path.exists():
            continue
        files[rel_path] = path.read_text(encoding="utf-8")
    return files


def list_question_names() -> List[str]:
    if not QUESTIONS_ROOT.exists():
        return []
    return sorted([p.name for p in QUESTIONS_ROOT.iterdir() if p.is_dir()])


def get_hidden_files(question_name: str) -> List[Path]:
    root = question_root(question_name)
    hidden_patterns = ["hiddenTests.py", "hidden_level2.py", "hidden_level3.py", "hidden_level4.py"]
    files: List[Path] = []
    for name in hidden_patterns:
        path = root / name
        if path.exists():
            files.append(path)
    return files


def materialize_question(question_name: str, destination: Path, override_files: Dict[str, str]) -> Tuple[QuestionConfig, Path]:
    """
    Copy question assets into a temp workspace. Visible files are taken from override_files (user code),
    other assets (desc, hidden tests) are copied from question folder.
    """
    cfg = load_question_config(question_name)
    root = question_root(question_name)
    destination.mkdir(parents=True, exist_ok=True)

    # Write visible files (user content overrides)
    for rel_path in cfg.visible_files:
        content = override_files.get(rel_path)
        if content is None:
            source_path = root / rel_path
            if source_path.exists():
                content = source_path.read_text(encoding="utf-8")
        if content is None:
            continue
        dest_path = destination / rel_path
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_text(content, encoding="utf-8")

    # Copy hidden tests and other supporting files
    for path in root.iterdir():
        if path.name in cfg.visible_files:
            continue
        if path.name == "question.json":
            continue
        dest_path = destination / path.name
        if path.is_file():
            dest_path.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    return cfg, destination
