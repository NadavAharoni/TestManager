#!/usr/bin/env python3
"""
docx_to_question.py
====================
Convert a Word (.docx) exam question into the exam-tool question directory format.

Output structure
----------------
<output_dir>/
    question.md       — question body (Markdown, RTL Hebrew preserved)
    a1.md … aN.md     — one file per answer
    <images>.png/jpg  — extracted images, referenced in the md files
    meta.yaml         — skeleton to fill in (type, tags, correct answers)

Usage
-----
    python docx_to_question.py q20.docx --out my-questions/q020-histograms
    python docx_to_question.py q20.docx   # defaults to ./<docx-stem>/

The script tries to detect the question body vs. answers:
  - If the entire doc is wrapped in a single numbered list item (item 1),
    the content of that item is the question + answers sub-list.
  - Otherwise, everything before the first numbered sub-list is the question
    body, and the numbered items are the answers.

Assumptions / limitations
--------------------------
- Answers are a numbered list (1. 2. 3. ...) in the document.
- Images embedded in the doc are extracted and referenced as
  ![](image1.png) etc. (relative - works from the question dir).
- Table-formatted images (pandoc grid tables) are converted to plain
  image lines, keeping the caption label as alt text.
- Math: $...$ and $$...$$ are passed through as-is (pandoc preserves them).
- RTL / Hebrew text: dir="rtl" pandoc span attributes are stripped;
  the language field in meta.yaml carries that info.
- meta.yaml is a skeleton -- fill in `correct:` and `tags:` by hand.
"""

import argparse
import re
import shutil
import sys
import subprocess
from pathlib import Path

import yaml  # pyyaml


# ---------------------------------------------------------------------------
# Pandoc
# ---------------------------------------------------------------------------

def run_pandoc(docx_path: Path, media_dir: Path) -> str:
    result = subprocess.run(
        [
            "pandoc",
            str(docx_path),
            "--from=docx",
            "--to=markdown",
            "--wrap=none",
            f"--extract-media={media_dir}",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return result.stdout


# ---------------------------------------------------------------------------
# Markdown clean-up
# ---------------------------------------------------------------------------

def clean_rtl_attrs(text: str) -> str:
    """Remove pandoc RTL span wrappers: [text]{dir="rtl"} -> text."""
    text = re.sub(r'\[([^\]]*)\]\{[^}]*dir="rtl"[^}]*\}', r'\1', text)
    text = re.sub(r'\[\]\{[^}]*\}', '', text)
    return text


def fix_image_syntax(text: str) -> str:
    """
    - Strip width/height attrs from images
    - Flatten filename: media/image1.png -> image1.png
    - Keep label text from table cell as alt text where available
    """
    def _clean_img(m):
        alt = m.group(1).strip()
        path = Path(m.group(2)).name
        return f"![{alt}]({path})" if alt else f"![]({path})"

    text = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)(?:\{[^}]*\})?', _clean_img, text)
    return text


def clean_grid_tables(text: str) -> str:
    """
    Remove pandoc grid-table separator lines (rows of dashes).
    The image and label content inside the table cells is preserved;
    only the structural separator lines are dropped.
    """
    lines = text.split('\n')
    out = []
    for line in lines:
        stripped = line.strip()
        # Grid table separator: line is all dashes, spaces, equals, pipes
        if stripped and re.match(r'^[-=| ]+$', stripped) and '-' in stripped:
            continue
        out.append(line)

    result = '\n'.join(out)
    result = re.sub(r'\n{3,}', '\n\n', result)
    return result


def strip_trailing_whitespace(text: str) -> str:
    return '\n'.join(line.rstrip() for line in text.split('\n'))


def clean_markdown(md: str) -> str:
    md = clean_rtl_attrs(md)
    md = fix_image_syntax(md)
    md = clean_grid_tables(md)
    md = strip_trailing_whitespace(md)
    return md.strip()


# ---------------------------------------------------------------------------
# Question / answer splitting
# ---------------------------------------------------------------------------

def split_question_answers(md: str):
    """
    Split markdown into (question_body, [answer1, answer2, ...]).

    Handles two common Word document structures:

    Structure A — question body as plain paragraphs, answers as a list:
        <question text>
        1.  answer one
        2.  answer two
        ...

    Structure B — question body formatted as a single list item,
    answers as a SEPARATE list that follows:
        1.  <question body text and images>

        1.  answer one
        2.  answer two
        ...

    Detection: if the document starts with "1.  " and the very next
    occurrence of "1.  " (at column 0) is a second separate list,
    we treat the first item as the question body and the second list
    as the answers.
    """
    item_re = re.compile(r'^(\d+)\.\s{1,3}', re.MULTILINE)
    all_matches = list(item_re.finditer(md))

    if not all_matches:
        return md.strip(), []

    # Find all positions where "1." starts (these are list restarts)
    one_matches = [m for m in all_matches if m.group(1) == '1']

    if len(one_matches) >= 2:
        # Structure B: first "1." = question body, second "1." = answer list
        first_list_start = one_matches[0]
        answer_list_start = one_matches[1]

        # Extract question body: content of first list item (between the two "1."s)
        q_raw = md[first_list_start.end(): answer_list_start.start()]
        # De-indent (pandoc indents list continuation by 4 spaces)
        q_lines = []
        for line in q_raw.split('\n'):
            q_lines.append(re.sub(r'^    ', '', line))
        question_body = '\n'.join(q_lines).strip()

    elif len(one_matches) == 1 and all_matches[0].group(1) == '1':
        # Structure A: plain question body before the list
        question_body = md[:all_matches[0].start()].strip()
        answer_list_start = all_matches[0]

    else:
        return md.strip(), []

    # Collect answer items from answer_list_start onward
    answer_matches = [m for m in all_matches if m.start() >= answer_list_start.start()]

    answers = []
    for i, m in enumerate(answer_matches):
        start = m.end()
        end = answer_matches[i + 1].start() if i + 1 < len(answer_matches) else len(md)
        answer_text = md[start:end].strip()
        answers.append(answer_text)

    return question_body, answers


# ---------------------------------------------------------------------------
# meta.yaml skeleton
# ---------------------------------------------------------------------------

def make_meta_yaml(num_answers: int, question_type: str = "single-choice") -> str:
    labels_he = ['א', 'ב', 'ג', 'ד', 'ה', 'ו', 'ז', 'ח', 'ט', 'י']
    answers = {}
    for i in range(1, num_answers + 1):
        label = labels_he[i - 1] if i <= len(labels_he) else str(i)
        if question_type == "single-choice":
            answers[f"a{i}"] = {"label": label, "correct": False}
        else:
            answers[f"a{i}"] = {"label": label, "correct": False, "weight": -1.0}

    meta = {
        "type": question_type,
        "language": "he",
        "tags": ["TODO"],
        "points": 5,
        "answers": answers,
    }
    header = "# Generated skeleton -- fill in 'correct' values and tags before use\n"
    return header + yaml.dump(meta, allow_unicode=True, default_flow_style=False, sort_keys=False)


# ---------------------------------------------------------------------------
# Main conversion
# ---------------------------------------------------------------------------

def convert(docx_path: Path, out_dir: Path, question_type: str):
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Run pandoc, extract media into a temp subdir
    tmp_media = out_dir / "_tmp_media"
    raw_md = run_pandoc(docx_path, tmp_media)

    # 2. Move extracted images directly into out_dir
    image_src = tmp_media / "media"
    if image_src.exists():
        for img in sorted(image_src.iterdir()):
            dest = out_dir / img.name
            shutil.move(str(img), dest)
            print(f"  image: {img.name}")
    if tmp_media.exists():
        shutil.rmtree(tmp_media)

    # 3. Clean markdown
    md = clean_markdown(raw_md)

    # 4. Split into question body + answers
    question_body, answers = split_question_answers(md)

    if not question_body:
        print("  WARNING: question body is empty -- check the docx structure.")
    if not answers:
        print("  WARNING: no answers detected -- check the docx structure.")

    # 5. Write question.md
    (out_dir / "question.md").write_text(question_body, encoding="utf-8")
    print(f"  question.md  ({len(question_body)} chars)")

    # 6. Write a1.md ... aN.md
    for i, ans_text in enumerate(answers, 1):
        fname = f"a{i}.md"
        (out_dir / fname).write_text(ans_text, encoding="utf-8")
        print(f"  {fname}  ({len(ans_text)} chars)")

    # 7. Write meta.yaml skeleton
    meta_text = make_meta_yaml(len(answers), question_type)
    (out_dir / "meta.yaml").write_text(meta_text, encoding="utf-8")
    print(f"  meta.yaml  ({len(answers)} answers, type={question_type})")

    print(f"\nDone -> {out_dir}")
    print("Next: open meta.yaml and set 'correct:' values and tags.")


def main():
    parser = argparse.ArgumentParser(
        description="Convert a Word exam question to exam-tool question directory format."
    )
    parser.add_argument("docx", help="Path to the .docx question file")
    parser.add_argument(
        "--out", "-o",
        help="Output directory (default: ./<docx-stem>/)",
        default=None,
    )
    parser.add_argument(
        "--type", "-t",
        choices=["single-choice", "multi-statement"],
        default="single-choice",
        help="Question type for meta.yaml (default: single-choice)",
    )
    args = parser.parse_args()

    docx_path = Path(args.docx).resolve()
    if not docx_path.exists():
        sys.exit(f"Error: file not found: {docx_path}")

    out_dir = Path(args.out) if args.out else Path(docx_path.stem)
    out_dir = out_dir.resolve()

    print(f"Converting: {docx_path.name}  ->  {out_dir}")
    convert(docx_path, out_dir, args.type)


if __name__ == "__main__":
    main()
