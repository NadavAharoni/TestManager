from pathlib import Path

import pytest

from src.assembler import assemble_exam
from src.models import QuestionType

EXAMPLE_DIR = Path(__file__).parent.parent / "example-questions"
DEMO_EXAM = EXAMPLE_DIR / "exams" / "demo.yaml"


def test_assemble_demo_exam():
    exam = assemble_exam(DEMO_EXAM, bank=EXAMPLE_DIR)
    assert exam.id == "demo-exam"
    assert len(exam.questions) == 2


def test_question_order():
    exam = assemble_exam(DEMO_EXAM, bank=EXAMPLE_DIR)
    assert exam.questions[0].id == "q-example-single"
    assert exam.questions[1].id == "q-example-multi"


def test_exam_metadata():
    exam = assemble_exam(DEMO_EXAM, bank=EXAMPLE_DIR)
    assert exam.title == "מבחן דוגמה"
    assert exam.duration_minutes == 60
    assert exam.shuffle_answers is False


def test_questions_fully_loaded():
    exam = assemble_exam(DEMO_EXAM, bank=EXAMPLE_DIR)
    for q in exam.questions:
        assert q.body.strip()
        assert len(q.answers) > 0


def test_missing_question_raises(tmp_path):
    import yaml

    exam_data = {
        "id": "bad-exam",
        "title": "Bad",
        "course": "Test",
        "date": "2026-01-01",
        "duration_minutes": 30,
        "instructions": "none",
        "questions": ["q-does-not-exist"],
    }
    exam_path = tmp_path / "bad.yaml"
    exam_path.write_text(yaml.dump(exam_data), encoding="utf-8")

    bank = tmp_path / "bank"
    bank.mkdir()

    with pytest.raises(FileNotFoundError, match="q-does-not-exist"):
        assemble_exam(exam_path, bank=bank)
