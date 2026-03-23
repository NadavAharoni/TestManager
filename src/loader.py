import warnings
from pathlib import Path

import yaml

from src.models import Answer, Question, QuestionType


def load_question(question_dir: Path) -> Question:
    """Load a question from its directory and return a Question dataclass."""
    question_dir = Path(question_dir)

    meta_path = question_dir / "meta.yaml"
    if not meta_path.exists():
        raise FileNotFoundError(f"Missing meta.yaml in {question_dir}")

    with open(meta_path, encoding="utf-8") as f:
        meta = yaml.safe_load(f)

    question_path = question_dir / "question.md"
    body = question_path.read_text(encoding="utf-8").strip()

    # Warn about answer files on disk that are not listed in meta.yaml
    declared_keys = set(meta.get("answers", {}).keys())
    for candidate in question_dir.glob("a*.md"):
        key = candidate.stem
        if key not in declared_keys:
            warnings.warn(
                f"{candidate.name} exists in {question_dir} but is not listed in meta.yaml — ignored",
                stacklevel=2,
            )

    answers: list[Answer] = []
    for file_key, ans_meta in meta.get("answers", {}).items():
        ans_path = question_dir / f"{file_key}.md"
        if not ans_path.exists():
            raise FileNotFoundError(
                f"Answer file {ans_path} is listed in meta.yaml but not found on disk"
            )
        text = ans_path.read_text(encoding="utf-8").strip()
        answers.append(
            Answer(
                file_key=file_key,
                label=ans_meta["label"],
                text=text,
                correct=bool(ans_meta["correct"]),
                weight=float(ans_meta.get("weight", 1.0)),
            )
        )

    if "id" in meta:
        warnings.warn(
            f"{meta_path}: 'id' in meta.yaml is ignored — "
            "the question id is taken from the directory name.",
            stacklevel=2,
        )

    return Question(
        id=question_dir.name,
        type=QuestionType(meta["type"]),
        language=meta.get("language", "en"),
        tags=meta.get("tags", []),
        body=body,
        answers=answers,
        points=float(meta.get("points", 5.0)),
        assets_dir=str(question_dir.resolve()),
    )
