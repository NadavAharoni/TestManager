import base64
import re
from pathlib import Path

import markdown as md_lib
from lxml import etree

from src.exporters.base import BaseExporter
from src.models import Answer, Exam, Question, QuestionType


# ---------------------------------------------------------------------------
# Text / markup helpers
# ---------------------------------------------------------------------------

def _normalize_math(expr: str) -> str:
    """Normalize LaTeX macros that MathJax doesn't support."""
    expr = expr.replace(r'\lbrack', '[').replace(r'\rbrack', ']')
    expr = expr.replace(r'\lbrace', '{').replace(r'\rbrace', '}')
    return expr


def _convert_math(text: str) -> str:
    """Convert LaTeX delimiters to Moodle's MathJax format.

    Must process $$ before $ to avoid partial matches.
    """
    # Block math: $$...$$ → \[...\]
    text = re.sub(
        r'\$\$(.*?)\$\$',
        lambda m: r'\[' + _normalize_math(m.group(1)) + r'\]',
        text,
        flags=re.DOTALL,
    )
    # Inline math: $...$ → \(...\)
    text = re.sub(
        r'\$([^\$]+?)\$',
        lambda m: r'\(' + _normalize_math(m.group(1)) + r'\)',
        text,
    )
    return text


_TABLE_STYLE = 'style="border-collapse: collapse;"'
_CELL_STYLE  = 'style="border: 1px solid black; padding: 4px 8px;"'


def _style_tables(html: str) -> str:
    """Inject inline styles on <table>, <th>, and <td> elements."""
    html = re.sub(r'<table>', f'<table {_TABLE_STYLE}>', html)
    html = re.sub(r'<(th|td)(\s|>)', rf'<\1 {_CELL_STYLE}\2', html)
    return html


def _md_to_html(text: str) -> str:
    html = md_lib.markdown(text, extensions=["tables", "fenced_code", "md_in_html"])
    return _style_tables(html)


def _rtl_wrap(html: str) -> str:
    return f'<div dir="rtl" style="text-align: start;">{html}</div>'


def _process_images(
    html: str, assets_dir: str
) -> tuple[str, list[tuple[str, str]]]:
    """Replace local image src values with @@PLUGINFILE@@/name and collect files.

    Returns (modified_html, [(filename, base64_content), ...]).
    """
    files: list[tuple[str, str]] = []
    assets_path = Path(assets_dir)

    def _replace(match: re.Match) -> str:
        src = match.group(1)
        if src.startswith(("http://", "https://", "@@PLUGINFILE@@")):
            return match.group(0)
        img_path = assets_path / src
        if img_path.exists():
            b64 = base64.b64encode(img_path.read_bytes()).decode("ascii")
            files.append((img_path.name, b64))
            return f'src="@@PLUGINFILE@@/{img_path.name}"'
        return match.group(0)

    html = re.sub(r'src="([^"]*)"', _replace, html)
    return html, files


# ---------------------------------------------------------------------------
# Grading
# ---------------------------------------------------------------------------

def _compute_fractions(answers: list[Answer], qtype: QuestionType) -> list[float]:
    if qtype == QuestionType.SINGLE_CHOICE:
        return [100.0 if a.correct else 0.0 for a in answers]

    # multi-statement: normalise weights against sum of positive weights
    sum_positive = sum(a.weight for a in answers if a.correct and a.weight > 0) or 1.0
    fractions = []
    for a in answers:
        if a.correct:
            fractions.append((a.weight / sum_positive) * 100.0)
        else:
            fractions.append(-(abs(a.weight) / sum_positive) * 100.0)
    return fractions


def _fmt_fraction(f: float) -> str:
    """Format a fraction value cleanly (no unnecessary decimals)."""
    if f == int(f):
        return str(int(f))
    return f"{f:.5f}".rstrip("0").rstrip(".")


# ---------------------------------------------------------------------------
# XML building
# ---------------------------------------------------------------------------

def _question_to_elem(question: Question, shuffle: bool) -> etree._Element:
    qelem = etree.Element("question", type="multichoice")

    # <name>
    name_elem = etree.SubElement(qelem, "name")
    etree.SubElement(name_elem, "text").text = question.id

    # <questiontext>
    body_html = _convert_math(_md_to_html(question.body))
    if question.language == "he":
        body_html = _rtl_wrap(body_html)
    body_html, img_files = _process_images(body_html, question.assets_dir)

    qtxt_elem = etree.SubElement(qelem, "questiontext", format="html")
    etree.SubElement(qtxt_elem, "text").text = etree.CDATA(body_html)
    for fname, fdata in img_files:
        felem = etree.SubElement(
            qtxt_elem, "file", name=fname, path="/", encoding="base64"
        )
        felem.text = fdata

    # Scalar fields
    etree.SubElement(qelem, "defaultgrade").text = _fmt_fraction(question.points)
    etree.SubElement(qelem, "shuffleanswers").text = "1" if shuffle else "0"
    etree.SubElement(qelem, "single").text = (
        "true" if question.type == QuestionType.SINGLE_CHOICE else "false"
    )
    etree.SubElement(qelem, "penalty").text = "0"

    # <answer> elements
    fractions = _compute_fractions(question.answers, question.type)
    for answer, fraction in zip(question.answers, fractions):
        ans_html = _convert_math(_md_to_html(answer.text))
        if question.language == "he":
            ans_html = _rtl_wrap(ans_html)
        aelem = etree.SubElement(
            qelem, "answer", fraction=_fmt_fraction(fraction), format="html"
        )
        etree.SubElement(aelem, "text").text = etree.CDATA(ans_html)
        feedback = etree.SubElement(aelem, "feedback")
        etree.SubElement(feedback, "text").text = ""

    return qelem


# ---------------------------------------------------------------------------
# Exporter
# ---------------------------------------------------------------------------

class MoodleExporter(BaseExporter):

    def export_exam(self, exam: Exam, output_dir: Path) -> Path:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        quiz = etree.Element("quiz")
        for question in exam.questions:
            quiz.append(_question_to_elem(question, exam.shuffle_answers))

        output_path = output_dir / f"{exam.id}.xml"
        self._write_xml(quiz, output_path)
        return output_path

    def export_question(self, question: Question, output_dir: Path) -> Path:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        quiz = etree.Element("quiz")
        quiz.append(_question_to_elem(question, shuffle=False))

        output_path = output_dir / f"{question.id}.xml"
        self._write_xml(quiz, output_path)
        return output_path

    @staticmethod
    def _write_xml(root: etree._Element, path: Path) -> None:
        tree = etree.ElementTree(root)
        tree.write(
            str(path),
            xml_declaration=True,
            encoding="UTF-8",
            pretty_print=True,
        )
