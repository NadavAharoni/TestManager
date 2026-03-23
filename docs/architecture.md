# Exam Management Tool — Claude Code Instructions

## Project Goal

Build a Python CLI tool for a teacher to:
1. Store exam questions in a structured Markdown + YAML format
2. Assemble exams from a question bank
3. Export to **Moodle XML** (Phase 1 priority)
4. Export to **PDF via Typst** (Phase 2 — add later as a separate exporter)

Primary exam language is **Hebrew** (RTL), mixed with LaTeX math (`$...$`),
English code snippets, tables, and images. There is no Hebrew inside equations.

---

## Repository Structure

```
exam-tool/
├── question-bank/
│   ├── q001-partition/
│   │   ├── question.md       # Question body + answer choices (Markdown + YAML frontmatter)
│   │   ├── meta.yaml         # Type, tags, correct answers, weights
│   │   └── diagram.png       # Optional assets referenced in question.md
│   ├── q002-merge-sort/
│   │   ├── question.md
│   │   └── meta.yaml
│   └── ...
├── exams/
│   └── algorithms-2024-a.yaml  # Exam definition: ordered list of question IDs + settings
├── output/                     # Generated files (add to .gitignore)
├── src/
│   ├── __init__.py
│   ├── models.py               # Dataclasses: Question, Answer, Exam
│   ├── loader.py               # Load and validate question-bank directories
│   ├── assembler.py            # Build an Exam object from an exam YAML file
│   └── exporters/
│       ├── __init__.py
│       ├── base.py             # Abstract BaseExporter class
│       └── moodle.py           # Moodle XML exporter (Phase 1)
│       # typst.py              # Typst/PDF exporter (Phase 2 — add later)
├── cli.py                      # CLI entry point
├── requirements.txt
└── README.md
```

---

## Question Format

### Directory layout

Each question lives in its own directory. The question body and each answer
are separate Markdown files. This allows answers to contain rich content —
formulas, code, images, tables — without cramming everything into a single file.

```
question-bank/
└── q008-heap-properties/
    ├── question.md   # question body only (no answers)
    ├── a1.md         # answer א
    ├── a2.md         # answer ב
    ├── a3.md         # answer ג
    ├── a4.md         # answer ד
    ├── a5.md         # answer ה
    ├── meta.yaml     # type, tags, correct/incorrect + weights per answer file
    └── diagram.png   # optional asset, referenced from question.md or any answer
```

Answer files are named `a1.md`, `a2.md`, … `aN.md`. The display label for each
answer (א, ב, ג… or A, B, C…) is defined in `meta.yaml`, not in the filename.
This keeps filenames simple and language-neutral.

---

### `question.md`

Contains **only the question body** — no answers. YAML frontmatter holds
question-level metadata. Math uses standard LaTeX delimiters (`$...$` inline,
`$$...$$` block). Images are standard Markdown image links, resolved relative
to the question directory.

#### Example — Single-choice question (q002-recurrence-merge)

```markdown
---
id: q002-recurrence-merge
type: single-choice
language: he
tags: [algorithms, sorting, recurrence]
---

לאיזה אלגוריתם מתאימה נוסחת הנסיגה הבאה?

$$T(1) = 0$$
$$T(n) = 2T\!\left(\frac{n}{2}\right) + n$$

ניתן להניח ש-$n$ הוא חזקה שלמה של $2$.
```

#### Example — Multi-statement question (q001-partition)

```markdown
---
id: q001-partition
type: multi-statement
language: he
tags: [algorithms, sorting, partition]
---

הפונקציה `partition` מקבלת בתור קלט מערך עם $N$ איברים.
סמני את הטענות הנכונות (אחת או יותר):
```

---

### Answer files (`a1.md`, `a2.md`, …)

Each answer is a standalone Markdown file. It contains **only the answer text**
— no label, no metadata. The label is in `meta.yaml`. The file may contain
anything valid in Markdown: inline math, block math, code spans, code blocks,
images, tables, plain text, or mixed RTL/LTR content.

#### Examples from question 8 (heap properties) and question 12 (BST insert time):

`a1.md`
```markdown
שני בנים של קדקד $X$ נמצאים תמיד באינדקסים סמוכים.
```

`a2.md`
```markdown
אם האינדקס הראשון של המערך הוא 0, ואם קדקד נמצא באינדקס $i$
אז הבנים נמצאים באינדקסים `i*2+1` ו-`i*2+2`.
```

`a3.md`
```markdown
אם האינדקס הראשון של המערך הוא 0, ואורך המערך הוא $n$,
אז לקדקדים שהאינדקס שלהם קטן מ-$\frac{n-1}{2}$ יש בנים.
```

`a4.md` (from q12 — answers that are pure complexity expressions)
```markdown
במקרה הגרוע $O(n^2)$ ובמקרה הכי טוב $O(n \cdot \log n)$
```

`a5.md`
```markdown
במקרה הגרוע $O(n^3)$ ובמקרה הכי טוב $O(n^2)$
```

---

### `meta.yaml`

Defines question type, tags, points, and the answer key. Each entry under
`answers` maps an answer file (`a1`, `a2`, …) to its display label, correctness,
and grading weight.

**`weight`** is only meaningful for `multi-statement` questions:
- Positive weight on a correct answer: student gains points for marking it
- Negative weight on an incorrect answer: student loses points for marking it
- Magnitude reflects how wrong/right the statement is (teacher's judgment)
- Weights are relative — exporters normalise them to whatever the target format requires

#### For `single-choice`:

```yaml
id: q002-recurrence-merge
type: single-choice
language: he
tags: [algorithms, sorting, recurrence]
points: 5
answers:
  a1: { label: "א", correct: false }
  a2: { label: "ב", correct: false }
  a3: { label: "ג", correct: true  }
  a4: { label: "ד", correct: false }
  a5: { label: "ה", correct: false }
```

#### For `multi-statement`:

```yaml
id: q001-partition
type: multi-statement
language: he
tags: [algorithms, sorting, partition]
points: 5
answers:
  a1: { label: "א", correct: true,  weight:  1.0 }
  a2: { label: "ב", correct: false, weight: -1.0 }  # very wrong — large penalty
  a3: { label: "ג", correct: false, weight: -0.5 }  # slightly wrong — small penalty
  a4: { label: "ד", correct: false, weight: -1.0 }
  a5: { label: "ה", correct: false, weight: -0.5 }
```

---

### Exam definition file (`exams/algorithms-2024-a.yaml`)

```yaml
id: algorithms-2024-a
title: "בחינה באלגוריתמים — סמסטר א תשפ״ו"
course: "אלגוריתמים ומבוא לעיבוד תמונה"
date: "2026-01-15"
duration_minutes: 90
instructions: "במבחן 20 שאלות, כל שאלה 5 נקודות. ללא חומר עזר."
questions:
  - q001-partition
  - q002-merge-sort
  - q003-recurrence-insertion
shuffle_answers: false   # preserve original answer order
```

---

## Data Models (`src/models.py`)

```python
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

class QuestionType(Enum):
    SINGLE_CHOICE = "single-choice"
    MULTI_STATEMENT = "multi-statement"

@dataclass
class Answer:
    label: str          # e.g. "א", "ב", "ג"
    text: str           # Markdown text of the answer
    correct: bool
    weight: float = 1.0 # Relative weight for grading

@dataclass
class Question:
    id: str
    type: QuestionType
    language: str       # "he", "en", etc.
    tags: list[str]
    body: str           # Markdown text of the question body
    answers: list[Answer]
    points: float = 5.0
    assets_dir: str = ""  # Path to the question directory (for resolving images)

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
```

---

## Loader (`src/loader.py`)

The loader:
1. Scans a question directory (e.g. `question-bank/q001-partition/`)
2. Reads `meta.yaml` to get question type, tags, points, and the answer manifest
   (which files exist, their labels, correctness, weights)
3. Reads `question.md` — strips YAML frontmatter, keeps the body as a Markdown string
4. For each answer entry in `meta.yaml` (`a1`, `a2`, ...), reads the corresponding
   `a{N}.md` file and stores its content as a Markdown string
5. Assembles and returns a validated `Question` dataclass

**Parsing rules:**
- YAML frontmatter in `question.md` is delimited by `---` at the top; use
  `python-frontmatter` to split it cleanly
- Answer files contain only Markdown -- no frontmatter, no labels
- Answer files are loaded in the order they appear in `meta.yaml`'s `answers` dict
- Missing answer files referenced in `meta.yaml` should raise a clear error

---

## Moodle XML Exporter (`src/exporters/moodle.py`)

### Overview

Moodle's XML quiz format supports:
- `multichoice` with `single="true"` — one correct answer → maps to `single-choice`
- `multichoice` with `single="false"` — multiple correct answers → maps to `multi-statement`

Moodle handles all visual formatting (fonts, RTL, layout) once the content is
imported, so the exporter only needs to produce valid XML with correct content
and grading values.

### Grading in Moodle XML

**Single-choice:** The correct answer gets `fraction="100"`, all others `fraction="0"`.

**Multi-statement:** Moodle's fraction is a percentage of the question's total
points. Derive fractions from the weights in `meta.yaml`:

```
# Correct answers (student should mark these):
fraction = (weight / sum_of_positive_weights) * 100

# Incorrect answers (penalty when student wrongly marks these):
fraction = -(weight_magnitude / sum_of_positive_weights) * 100
```

Fractions for all correct answers must sum to exactly 100.
Set the `penalty` attribute to 0 (non-adaptive mode).

### Math rendering in Moodle

Moodle renders LaTeX via its built-in MathJax filter. Convert delimiters:
- Inline: `$...$` → `\(...\)`
- Block: `$$...$$` → `\[...\]`

### HTML in Moodle XML

Question and answer text is wrapped in `<![CDATA[...]]>` and treated as HTML.
Convert Markdown to HTML using the `markdown` Python library before inserting.

For Hebrew (RTL) content, wrap in:
`<div dir="rtl" style="text-align: right;">...</div>`

Code blocks: `<pre><code>...</code></pre>` (the `markdown` library handles this).

### Images

Images referenced in Markdown (`![alt](filename.png)`) must be base64-encoded
and embedded in the XML as a `<file>` element. Resolve image paths relative to
the question's `assets_dir`.

```xml
<file name="diagram.png" path="/" encoding="base64">
  {base64_encoded_content}
</file>
```

Update the `<img>` src in the HTML to `@@PLUGINFILE@@/diagram.png` — this is
Moodle's convention for embedded question files.

### Output XML structure

```xml
<?xml version="1.0" encoding="UTF-8"?>
<quiz>
  <question type="multichoice">
    <name><text>q001-partition</text></name>
    <questiontext format="html">
      <text><![CDATA[
        <div dir="rtl" style="text-align: right;">
          {html_of_question_body}
        </div>
      ]]></text>
      <file name="diagram.png" path="/" encoding="base64">...</file>
    </questiontext>
    <defaultgrade>5</defaultgrade>
    <shuffleanswers>0</shuffleanswers>
    <single>false</single>
    <answer fraction="50" format="html">
      <text><![CDATA[{html_of_answer_text}]]></text>
      <feedback><text></text></feedback>
    </answer>
    <!-- ... more answers ... -->
  </question>
  <!-- ... more questions ... -->
</quiz>
```

---

## CLI (`cli.py`)

```
Usage:
  python cli.py export moodle --exam exams/algorithms-2024-a.yaml --output output/
  python cli.py export moodle --question question-bank/q001-partition/ --output output/
  python cli.py validate --exam exams/algorithms-2024-a.yaml
  python cli.py validate --question question-bank/q001-partition/
  python cli.py list-questions [--tag algorithms] [--type multi-statement]
```

Use `click` for the CLI.

---

## Exporter Interface (`src/exporters/base.py`)

All exporters must implement this interface so new exporters (Typst/PDF, etc.)
can be added later without changing any other code:

```python
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
```

---

## Dependencies (`requirements.txt`)

```
pyyaml              # YAML parsing
markdown            # Markdown → HTML conversion
click               # CLI
python-frontmatter  # Parse Markdown + YAML frontmatter cleanly
lxml                # XML generation
```

---

## Implementation Order

Build and test in this order:

1. `src/models.py` — data classes (no dependencies)
2. `src/loader.py` — parse one question directory; write unit tests with the
   sample questions below
3. `src/assembler.py` — load an exam YAML, resolve question IDs to Question objects
4. `src/exporters/base.py` — abstract interface
5. `src/exporters/moodle.py` — Moodle XML exporter
6. `cli.py` — wire everything together
7. End-to-end test covering:
   - single-choice with a math block
   - multi-statement with an image
   - question with a code snippet

---

## Sample Questions to Create for Testing

Create these in `question-bank/` immediately so there is real data to test
against. They are based on the teacher's actual algorithms exam.

### `question-bank/q001-partition/` (multi-statement, no image)

Question 1 from the exam: the `partition` function, five statements, two correct.
Files: `question.md` + `a1.md` through `a5.md` + `meta.yaml`.
Answers include inline math and inline code -- good test for mixed content.

### `question-bank/q008-heap-properties/` (multi-statement, formulas in answers)

Question 8 from the exam: heap (max-heap) properties, five statements.
Files: `question.md` + `a1.md` through `a5.md` + `meta.yaml`.
Answer a3 contains $\frac{n-1}{2}$; answer a2 contains `i*2+1` and `i*2+2`.
This is the primary test case for math and code inside answer files.

### `question-bank/q002-recurrence-merge/` (single-choice, math block in question)

Question 2 from the exam: given a recurrence relation (displayed equation in the
question body), identify which algorithm it describes.
Files: `question.md` + `a1.md` through `a5.md` + `meta.yaml`.

### `question-bank/q010-python-sort/` (single-choice, code block in question)

Question 10 from the exam: a Python code snippet using `sorted()` with a lambda,
four answer choices. Tests code block handling in the question body.

---

## Important Notes

- **No Hebrew inside math.** Math blocks are always pure LaTeX/ASCII.
- **RTL wrapping.** Apply `dir="rtl"` at the question/answer div level in HTML.
  Do not attempt to handle mixed RTL/LTR inside Markdown — let the browser and
  Moodle handle it via the Unicode bidirectional algorithm.
- **Answer labels.** Hebrew letter labels (א, ב, ג…) appear in `question.md`
  answer bullets. Keep them in the exported text so cross-references in question
  bodies (e.g. "ראי תשובה ב") remain meaningful inside Moodle.
- **Validation.** The `validate` command must check: all question IDs in the
  exam YAML exist in the question bank; `meta.yaml` has entries for every answer
  label listed in `question.md`; fractions for multi-statement questions sum
  to 100.
- **Encoding.** All source files are UTF-8. The XML output must declare
  `<?xml version="1.0" encoding="UTF-8"?>`.
- **Phase 2 (Typst PDF).** When the Typst exporter is added later, it will
  receive the same `Exam` and `Question` objects from the unchanged
  loader/assembler. No modifications to models, loader, or assembler will
  be needed — only a new `src/exporters/typst.py` file.
