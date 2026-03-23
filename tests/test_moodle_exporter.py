from pathlib import Path

import pytest
from lxml import etree

from src.assembler import assemble_exam
from src.exporters.moodle import MoodleExporter, _compute_fractions, _convert_math
from src.loader import load_question
from src.models import QuestionType

EXAMPLE_DIR = Path(__file__).parent.parent / "example-questions"
DEMO_EXAM = EXAMPLE_DIR / "exams" / "demo.yaml"


# ---------------------------------------------------------------------------
# Math conversion
# ---------------------------------------------------------------------------

def test_convert_inline_math():
    result = _convert_math("סיבוכיות $O(n)$ היא לינארית")
    assert r"\(O(n)\)" in result
    assert "$" not in result


def test_convert_block_math():
    result = _convert_math("$$x^2 + y^2 = r^2$$")
    assert r"\[x^2 + y^2 = r^2\]" in result
    assert "$$" not in result


def test_convert_block_before_inline():
    # $$...$$ must not be partially matched by the inline $...$ rule
    result = _convert_math("$$a + b$$")
    assert r"\[" in result
    assert r"\(" not in result


# ---------------------------------------------------------------------------
# Fraction calculation
# ---------------------------------------------------------------------------

def test_single_choice_fractions():
    q = load_question(EXAMPLE_DIR / "q-example-single")
    fractions = _compute_fractions(q.answers, QuestionType.SINGLE_CHOICE)
    assert fractions.count(100.0) == 1
    assert all(f == 0.0 for f in fractions if f != 100.0)


def test_multi_statement_fractions_sum_to_100():
    q = load_question(EXAMPLE_DIR / "q-example-multi")
    fractions = _compute_fractions(q.answers, QuestionType.MULTI_STATEMENT)
    positive_sum = sum(f for f in fractions if f > 0)
    assert abs(positive_sum - 100.0) < 0.01


def test_multi_statement_penalties_are_negative():
    q = load_question(EXAMPLE_DIR / "q-example-multi")
    fractions = _compute_fractions(q.answers, QuestionType.MULTI_STATEMENT)
    for answer, fraction in zip(q.answers, fractions):
        if not answer.correct:
            assert fraction < 0


# ---------------------------------------------------------------------------
# XML structure
# ---------------------------------------------------------------------------

def test_export_exam_creates_file(tmp_path):
    exam = assemble_exam(DEMO_EXAM, bank=EXAMPLE_DIR)
    out = MoodleExporter().export_exam(exam, tmp_path)
    assert out.exists()
    assert out.suffix == ".xml"


def test_export_exam_question_count(tmp_path):
    exam = assemble_exam(DEMO_EXAM, bank=EXAMPLE_DIR)
    out = MoodleExporter().export_exam(exam, tmp_path)
    root = etree.parse(str(out)).getroot()
    assert root.tag == "quiz"
    assert len(root.findall("question")) == 2


def test_single_choice_xml(tmp_path):
    q = load_question(EXAMPLE_DIR / "q-example-single")
    out = MoodleExporter().export_question(q, tmp_path)
    root = etree.parse(str(out)).getroot()
    question_elem = root.find("question")
    assert question_elem.get("type") == "multichoice"
    assert question_elem.find("single").text == "true"
    assert question_elem.find("penalty").text == "0"
    assert len(root.findall(".//answer")) == 4


def test_multi_statement_xml(tmp_path):
    q = load_question(EXAMPLE_DIR / "q-example-multi")
    out = MoodleExporter().export_question(q, tmp_path)
    root = etree.parse(str(out)).getroot()
    assert root.find(".//single").text == "false"


def test_no_raw_dollar_signs_in_output(tmp_path):
    exam = assemble_exam(DEMO_EXAM, bank=EXAMPLE_DIR)
    out = MoodleExporter().export_exam(exam, tmp_path)
    content = out.read_text(encoding="utf-8")
    assert "$" not in content


def test_rtl_wrapper_present(tmp_path):
    q = load_question(EXAMPLE_DIR / "q-example-single")
    assert q.language == "he"
    out = MoodleExporter().export_question(q, tmp_path)
    content = out.read_text(encoding="utf-8")
    assert 'dir="rtl"' in content


def test_export_question_creates_file(tmp_path):
    q = load_question(EXAMPLE_DIR / "q-example-single")
    out = MoodleExporter().export_question(q, tmp_path)
    assert out.exists()
    assert out.name == f"{q.id}.xml"
