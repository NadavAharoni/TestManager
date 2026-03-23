from pathlib import Path

import yaml

from src.loader import load_question
from src.models import Exam


def _resolve_bank(bank_flag: str | None, project_root: Path) -> Path:
    """Resolve bank path using the three-level priority order."""
    if bank_flag:
        return Path(bank_flag)

    config_path = Path.cwd() / ".examtool.yaml"
    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
        if "bank" in config:
            return Path(config["bank"])

    return project_root / "question-bank"


def assemble_exam(
    exam_path: Path,
    bank: Path | None = None,
    project_root: Path | None = None,
) -> Exam:
    """Read an exam YAML, resolve all question IDs, and return an Exam dataclass."""
    exam_path = Path(exam_path)

    if project_root is None:
        project_root = Path(__file__).parent.parent

    bank_path = _resolve_bank(str(bank) if bank else None, project_root)

    with open(exam_path, encoding="utf-8") as f:
        exam_data = yaml.safe_load(f)

    questions = []
    for qid in exam_data["questions"]:
        qdir = bank_path / qid
        if not qdir.exists():
            raise FileNotFoundError(
                f"Question directory not found: {qdir}  (bank: {bank_path})"
            )
        questions.append(load_question(qdir))

    return Exam(
        id=exam_data["id"],
        title=exam_data["title"],
        course=exam_data["course"],
        date=str(exam_data["date"]),
        duration_minutes=int(exam_data["duration_minutes"]),
        instructions=exam_data["instructions"],
        questions=questions,
        shuffle_answers=bool(exam_data.get("shuffle_answers", False)),
    )
