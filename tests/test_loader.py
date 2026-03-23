from pathlib import Path

import pytest
import yaml

from src.loader import load_question
from src.models import QuestionType

EXAMPLE_DIR = Path(__file__).parent.parent / "example-questions"


def test_load_single_choice():
    q = load_question(EXAMPLE_DIR / "q-example-single")
    assert q.id == "q-example-single"
    assert q.type == QuestionType.SINGLE_CHOICE
    assert q.language == "he"
    assert len(q.answers) == 4
    correct = [a for a in q.answers if a.correct]
    assert len(correct) == 1
    assert correct[0].label == "ג"


def test_load_multi_statement():
    q = load_question(EXAMPLE_DIR / "q-example-multi")
    assert q.id == "q-example-multi"
    assert q.type == QuestionType.MULTI_STATEMENT
    assert len(q.answers) == 4
    correct = [a for a in q.answers if a.correct]
    assert len(correct) == 2


def test_answer_labels_preserved():
    q = load_question(EXAMPLE_DIR / "q-example-single")
    labels = [a.label for a in q.answers]
    assert labels == ["א", "ב", "ג", "ד"]


def test_answer_text_nonempty():
    q = load_question(EXAMPLE_DIR / "q-example-multi")
    for answer in q.answers:
        assert answer.text.strip(), f"Answer {answer.file_key} has empty text"


def test_assets_dir_is_absolute():
    q = load_question(EXAMPLE_DIR / "q-example-single")
    assert Path(q.assets_dir).is_absolute()


def test_multi_statement_weights():
    q = load_question(EXAMPLE_DIR / "q-example-multi")
    weights = {a.file_key: a.weight for a in q.answers}
    assert weights["a1"] == 1.0
    assert weights["a2"] == -1.0
    assert weights["a3"] == 1.0
    assert weights["a4"] == -0.5


def test_id_from_directory_name(tmp_path):
    q_dir = tmp_path / "my-question-dir"
    q_dir.mkdir()
    meta = {"type": "single-choice", "language": "en", "tags": [], "points": 5,
            "answers": {"a1": {"label": "A", "correct": True}}}
    (q_dir / "meta.yaml").write_text(yaml.dump(meta), encoding="utf-8")
    (q_dir / "question.md").write_text("Body", encoding="utf-8")
    (q_dir / "a1.md").write_text("Answer", encoding="utf-8")
    q = load_question(q_dir)
    assert q.id == "my-question-dir"


def test_id_in_meta_yaml_warns(tmp_path):
    q_dir = tmp_path / "my-question-dir"
    q_dir.mkdir()
    meta = {"id": "something-else", "type": "single-choice", "language": "en",
            "tags": [], "points": 5, "answers": {"a1": {"label": "A", "correct": True}}}
    (q_dir / "meta.yaml").write_text(yaml.dump(meta), encoding="utf-8")
    (q_dir / "question.md").write_text("Body", encoding="utf-8")
    (q_dir / "a1.md").write_text("Answer", encoding="utf-8")
    with pytest.warns(UserWarning, match="'id' in meta.yaml is ignored"):
        q = load_question(q_dir)
    assert q.id == "my-question-dir"


def test_missing_meta_yaml(tmp_path):
    with pytest.raises(FileNotFoundError, match="meta.yaml"):
        load_question(tmp_path)


def test_missing_answer_file(tmp_path):
    meta = {
        "type": "single-choice",
        "language": "en",
        "tags": [],
        "points": 5,
        "answers": {
            "a1": {"label": "A", "correct": True},
        },
    }
    (tmp_path / "meta.yaml").write_text(yaml.dump(meta), encoding="utf-8")
    (tmp_path / "question.md").write_text("Body", encoding="utf-8")
    # a1.md intentionally absent
    with pytest.raises(FileNotFoundError, match="a1.md"):
        load_question(tmp_path)
