from abc import ABC, abstractmethod
from pathlib import Path

from src.models import Exam, Question


class BaseExporter(ABC):

    @abstractmethod
    def export_exam(self, exam: Exam, output_dir: Path) -> Path:
        """Export a full exam. Returns path to the output file."""
        ...

    @abstractmethod
    def export_question(self, question: Question, output_dir: Path) -> Path:
        """Export a single question (useful for previewing/testing)."""
        ...
