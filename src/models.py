from dataclasses import dataclass, field
from enum import Enum


class QuestionType(Enum):
    SINGLE_CHOICE   = "single-choice"
    MULTI_STATEMENT = "multi-statement"


@dataclass
class Answer:
    file_key: str       # "a1", "a2", … — matches key in meta.yaml
    label: str          # display label, e.g. "א", "ב", "A", "B"
    text: str           # Markdown content of the answer file
    correct: bool
    weight: float = 1.0  # relative grading weight (multi-statement only)


@dataclass
class Question:
    id: str
    type: QuestionType
    language: str        # "he", "en", etc.
    tags: list[str]
    body: str            # Markdown content of question.md
    answers: list[Answer]
    points: float = 5.0
    assets_dir: str = ""  # absolute path to the question directory


@dataclass
class Exam:
    id: str
    title: str
    course: str
    date: str
    duration_minutes: int
    instructions: str
    questions: list[Question]
    shuffle_answers: bool = False
