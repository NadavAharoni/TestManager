# Exam Management Tool — Architecture

## Project Goal

A Python CLI tool for a teacher to:
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
│   │   ├── question.md   # question body only
│   │   ├── a1.md         # answer א
│   │   ├── a2.md         # answer ב
│   │   ├── a3.md         # answer ג
│   │   ├── a4.md         # answer ד
│   │   ├── a5.md         # answer ה
│   │   ├── meta.yaml     # type, tags, correct/incorrect + weights per answer
│   │   └── diagram.png   # optional asset, referenced from question.md or any answer
│   ├── q002-recurrence-merge/
│   │   └── ...
│   └── ...
├── exams/
│   └── algorithms-2024-a.yaml  # ordered list of question IDs + exam settings
├── output/                     # generated files — gitignored
├── src/
│   ├── __init__.py
│   ├── models.py               # dataclasses: Question, Answer, Exam
│   ├── loader.py               # load and validate a question directory
│   ├── assembler.py            # build an Exam object from an exam YAML
│   └── exporters/
│       ├── __init__.py
│       ├── base.py             # abstract BaseExporter
│       └── moodle.py           # Moodle XML exporter (Phase 1)
│       # typst.py              # Typst/PDF exporter (Phase 2 — add later)
├── docs/
│   └── architecture.md         # this file
├── CLAUDE.md
├── cli.py
├── requirements.txt
└── README.md
```

---

## Question Format

### Directory layout

Each question lives in its own directory. The question body and each answer
are **separate Markdown files**. This allows answers to contain rich content —
formulas, code, images, tables — without cramming everything into one file.

Answer files are named `a1.md`, `a2.md`, … `aN.md`. The display label for each
answer (א, ב, ג… or A, B, C…) is defined in `meta.yaml`, not in the filename,
keeping filenames simple and language-neutral.

---

### `question.md`

Contains **only the question body** — no answers. YAML frontmatter holds
question-level metadata. Math uses standard LaTeX delimiters (`$...$` inline,
`$$...$$` block). Images are standard Markdown image links, resolved relative
to the question directory.

#### Example — single-choice question

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

#### Example — multi-statement question

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

Each answer is a standalone Markdown file containing **only the answer text** —
no label, no metadata. The file may contain anything valid in Markdown: inline
math, block math, code spans, code blocks, images, tables, plain text, or
mixed RTL/LTR content.

#### Examples from question 8 (heap properties)

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

#### Examples from question 12 (BST insert time) — pure complexity expressions

`a4.md`
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
- Magnitude reflects how wrong the statement is (teacher's judgment)
- Weights are relative — exporters normalise them to the target format's scale

#### For `single-choice`

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

#### For `multi-statement`

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

### Exam definition file

```yaml
id: algorithms-2024-a
title: "בחינה באלגוריתמים — סמסטר א תשפ״ו"
course: "אלגוריתמים ומבוד לעיבוד תמונה"
date: "2026-01-15"
duration_minutes: 90
instructions: "במבחן 20 שאלות, כל שאלה 5 נקודות. ללא חומר עזר."
questions:
  - q001-partition
  - q002-recurrence-merge
  - q008-heap-properties
shuffle_answers: false   # preserve original answer order
```

---

## Data Models (`src/models.py`)

```python
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
    weight: float = 1.0 # relative grading weight (multi-statement only)

@dataclass
class Question:
    id: str
    type: QuestionType
    language: str       # "he", "en", etc.
    tags: list[str]
    body: str           # Markdown content of question.md (frontmatter stripped)
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
```

---

## Loader (`src/loader.py`)

The loader reads one question directory and returns a `Question` dataclass.

Steps:
1. Read `meta.yaml` — get type, tags, points, and the answer manifest
2. Read `question.md` using `python-frontmatter` — strip frontmatter, keep body
3. For each key in `meta.yaml`'s `answers` dict (`a1`, `a2`, …), read the
   corresponding `a{N}.md` file as a Markdown string
4. Build and return a validated `Question`

**Error handling:**
- Missing `meta.yaml` → clear error naming the directory
- Answer file listed in `meta.yaml` but not found on disk → clear error naming
  the missing file
- `meta.yaml` missing entries for a file that exists on disk → warning only
  (the extra file is ignored)

---

## Assembler (`src/assembler.py`)

Reads an exam YAML file, resolves each question ID to a directory in the
question bank, calls the loader for each, and returns an `Exam` dataclass.

The question bank root defaults to `question-bank/` relative to the project
root, but should be configurable (e.g. via CLI option or env var) to support
multiple question banks.

---

## Exporter Interface (`src/exporters/base.py`)

All exporters implement this interface. Adding a new output format (e.g. Typst)
means adding a new file — no changes to models, loader, or assembler.

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

## Moodle XML Exporter (`src/exporters/moodle.py`)

### Question types

- `single-choice` → `<question type="multichoice">` with `<single>true</single>`
- `multi-statement` → `<question type="multichoice">` with `<single>false</single>`

Moodle handles all visual formatting (fonts, RTL, layout) after import, so the
exporter only needs correct content and grading values.

### Grading

**Single-choice:** correct answer gets `fraction="100"`, all others `fraction="0"`.

**Multi-statement:** derive fractions from `meta.yaml` weights:

```
# Correct answers (student should mark these):
fraction = (weight / sum_of_positive_weights) * 100

# Incorrect answers (penalty if student wrongly marks these):
fraction = -(abs(weight) / sum_of_positive_weights) * 100
```

Fractions for all correct answers must sum to exactly 100.
Set `penalty="0"` (non-adaptive exams).

### Math

Convert LaTeX delimiters for Moodle's MathJax filter:
- Inline: `$...$` → `\(...\)`
- Block: `$$...$$` → `\[...\]`

### HTML

Question and answer text is wrapped in `<![CDATA[...]]>` and treated as HTML.
Convert Markdown → HTML using the `markdown` Python library.

For Hebrew (RTL) content wrap in:
```html
<div dir="rtl" style="text-align: right;">...</div>
```

Apply this wrapper at the question level and at each answer level when
`language: he`.

### Images

Base64-encode images and embed them as `<file>` elements. Update `<img>` src
to use Moodle's `@@PLUGINFILE@@` convention:

```xml
<questiontext format="html">
  <text><![CDATA[
    <div dir="rtl" style="text-align: right;">
      <img src="@@PLUGINFILE@@/diagram.png" />
    </div>
  ]]></text>
  <file name="diagram.png" path="/" encoding="base64">
    {base64_content}
  </file>
</questiontext>
```

Resolve image paths relative to `question.assets_dir`.

### Full XML structure

```xml
<?xml version="1.0" encoding="UTF-8"?>
<quiz>
  <question type="multichoice">
    <name><text>q001-partition</text></name>
    <questiontext format="html">
      <text><![CDATA[
        <div dir="rtl" style="text-align: right;">
          {html_question_body}
        </div>
      ]]></text>
    </questiontext>
    <defaultgrade>5</defaultgrade>
    <shuffleanswers>0</shuffleanswers>
    <single>false</single>
    <penalty>0</penalty>
    <answer fraction="50" format="html">
      <text><![CDATA[
        <div dir="rtl" style="text-align: right;">
          {html_answer_text}
        </div>
      ]]></text>
      <feedback><text></text></feedback>
    </answer>
    <!-- ... more <answer> elements ... -->
  </question>
  <!-- ... more <question> elements ... -->
</quiz>
```

---

## CLI (`cli.py`)

Use `click`.

```
python cli.py export moodle --exam exams/algorithms-2024-a.yaml --output output/
python cli.py export moodle --question question-bank/q001-partition/ --output output/
python cli.py validate --exam exams/algorithms-2024-a.yaml
python cli.py validate --question question-bank/q001-partition/
python cli.py list-questions [--tag algorithms] [--type multi-statement]
```

`validate` checks:
- All question IDs in the exam YAML exist in the question bank
- Every answer file referenced in `meta.yaml` exists on disk
- For `multi-statement`: fractions derived from weights sum to 100
- All files are valid UTF-8

---

## Dependencies (`requirements.txt`)

```
pyyaml              # YAML parsing
markdown            # Markdown → HTML
click               # CLI
python-frontmatter  # split YAML frontmatter from Markdown body
lxml                # XML generation
```

---

## Implementation Order

1. `src/models.py` — data classes, no dependencies
2. `src/loader.py` — parse one question directory; write unit tests using the
   sample questions below
3. `src/assembler.py` — load an exam YAML, resolve question IDs
4. `src/exporters/base.py` — abstract interface
5. `src/exporters/moodle.py` — Moodle XML exporter
6. `cli.py` — wire everything together
7. End-to-end test covering all three sample question types

---

## Sample Questions to Create for Testing

Create these in `question-bank/` immediately so there is real data to test
against. They are taken from the teacher's algorithms exam.

### `question-bank/q001-partition/`
Multi-statement, no images. Question 1 from the exam: the `partition` function,
five statements, two correct. Answers include inline math and inline code —
tests mixed content in answer files.

### `question-bank/q008-heap-properties/`
Multi-statement, no images. Question 8 from the exam: max-heap properties,
five statements. Answer `a3.md` contains $\frac{n-1}{2}$; answer `a2.md`
contains `i*2+1` and `i*2+2`. Primary test case for math and code inside
answer files.

### `question-bank/q002-recurrence-merge/`
Single-choice, math block in question body. Question 2 from the exam: identify
the algorithm from its recurrence relation. Tests block math in `question.md`.

### `question-bank/q010-python-sort/`
Single-choice, code block in question body. Question 10 from the exam: a Python
snippet using `sorted()` with a lambda. Tests fenced code block handling in
the question body and in Moodle HTML output.

---

## Phase 2 Note — Typst PDF Exporter

When adding the Typst exporter later:
- Add `src/exporters/typst.py` implementing `BaseExporter`
- No changes to models, loader, assembler, or existing exporters
- Typst handles Hebrew RTL natively and has cleaner math support than XeLaTeX
- Test Hebrew RTL rendering before committing to Typst as the PDF backend
