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
    python docx_to_question.py q20.docx   # defaults to the docx file's directory

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
- Tables (pandoc grid tables) are converted to HTML <table> elements.
  Cell content may contain markdown (images, text); cells are marked
  with markdown="1" so downstream processors (Python-Markdown md_in_html
  extension) render embedded markdown correctly.
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
    Convert markdown images to <img> tags.
    - Strip width/height attrs
    - Flatten filename: media/image1.png -> image1.png
    - HTML <img> renders correctly in VS Code / GitHub previews and passes
      through the Moodle exporter's src="..." substitution unchanged.
    """
    def _to_img_tag(m):
        alt = m.group(1).strip()
        path = Path(m.group(2)).name
        return f'<img src="{path}" alt="{alt}">' if alt else f'<img src="{path}">'

    text = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)(?:\{[^}]*\})?', _to_img_tag, text)
    return text


def _parse_grid_table(table_lines):
    """
    Parse pandoc grid table lines into ([], body_rows).
    All rows are treated as body rows — +===+ separators are ignored
    since Word tables don't reliably map to semantic headers.
    Each row is a list of cell strings (may contain markdown).
    """
    sep_indices = []
    for idx, line in enumerate(table_lines):
        stripped = line.strip()
        if re.match(r'^\+[-=+]+\+$', stripped):
            sep_indices.append((idx, '=' in stripped))

    if len(sep_indices) < 2:
        return [], []

    first_sep = table_lines[sep_indices[0][0]].strip()
    col_count = first_sep.count('+') - 1

    def extract_cells(content_lines):
        cells = [''] * col_count
        for line in content_lines:
            stripped = line.strip()
            if not stripped.startswith('|'):
                continue
            inner = stripped[1:]
            if inner.endswith('|'):
                inner = inner[:-1]
            parts = inner.split('|')
            for i, part in enumerate(parts[:col_count]):
                content = part.strip()
                if content:
                    cells[i] = (cells[i] + '\n' + content).strip()
        return cells

    rows = []
    for i in range(len(sep_indices) - 1):
        sep_idx = sep_indices[i][0]
        next_sep_idx = sep_indices[i + 1][0]
        content_lines = table_lines[sep_idx + 1:next_sep_idx]
        if not any(l.strip() for l in content_lines):
            continue
        rows.append(extract_cells(content_lines))

    return [], rows


def _grid_table_to_html(table_lines):
    """Convert pandoc grid table lines to an HTML <table> string."""
    header_rows, body_rows = _parse_grid_table(table_lines)
    if not header_rows and not body_rows:
        return '\n'.join(table_lines)

    parts = ['<table>']
    for row in body_rows:
        parts.append('<tr>')
        for cell in row:
            parts.append(f'<td markdown="1">\n{cell}\n</td>')
        parts.append('</tr>')
    parts.append('</table>')
    return '\n'.join(parts)


def clean_grid_tables(text: str) -> str:
    """
    Convert pandoc grid tables to HTML <table> elements.

    Scans for grid table blocks (lines starting with + or |) and replaces
    each with an HTML table. Cell content is preserved as markdown inside
    markdown="1" attributes for downstream processors.
    """
    lines = text.split('\n')
    result = []
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if re.match(r'^\+[-=+]+\+$', stripped):
            table_lines = []
            while i < len(lines):
                s = lines[i].strip()
                if re.match(r'^\+[-=+]+\+$', s) or s.startswith('|'):
                    table_lines.append(lines[i])
                    i += 1
                else:
                    break
            result.append(_grid_table_to_html(table_lines))
        else:
            result.append(lines[i])
            i += 1

    out = '\n'.join(result)
    out = re.sub(r'\n{3,}', '\n\n', out)
    return out


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

def find_yaml_in_dir(directory: Path):
    """
    Return the single yaml file in directory, or None if none exist.
    Exits with an error if more than one yaml file is found.
    """
    yaml_files = list(directory.glob("*.yaml")) + list(directory.glob("*.yml"))
    if len(yaml_files) > 1:
        sys.exit(
            f"Error: multiple YAML files found in {directory}:\n"
            + "\n".join(f"  {f.name}" for f in yaml_files)
            + "\nRemove all but one before running."
        )
    return yaml_files[0] if yaml_files else None


def convert(docx_path: Path, out_dir: Path, question_type: str):
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Check for existing yaml before doing any work
    existing_yaml = find_yaml_in_dir(out_dir)

    # 2. Run pandoc, extract media into a temp subdir
    tmp_media = out_dir / "_tmp_media"
    raw_md = run_pandoc(docx_path, tmp_media)

    # 3. Move extracted images directly into out_dir
    image_src = tmp_media / "media"
    if image_src.exists():
        for img in sorted(image_src.iterdir()):
            dest = out_dir / img.name
            shutil.move(str(img), dest)
            print(f"  image: {img.name}")
    if tmp_media.exists():
        shutil.rmtree(tmp_media)

    # 4. Clean markdown
    md = clean_markdown(raw_md)

    # 5. Split into question body + answers
    question_body, answers = split_question_answers(md)

    if not question_body:
        print("  WARNING: question body is empty -- check the docx structure.")
    if not answers:
        print("  WARNING: no answers detected -- check the docx structure.")

    # 6. Write question.md
    (out_dir / "question.md").write_text(question_body, encoding="utf-8")
    print(f"  question.md  ({len(question_body)} chars)")

    # 7. Write a1.md ... aN.md
    for i, ans_text in enumerate(answers, 1):
        fname = f"a{i}.md"
        (out_dir / fname).write_text(ans_text, encoding="utf-8")
        print(f"  {fname}  ({len(ans_text)} chars)")

    # 8. Handle meta.yaml
    if existing_yaml:
        with open(existing_yaml, encoding="utf-8") as f:
            existing_meta = yaml.safe_load(f)
        yaml_answers = existing_meta.get("answers", {})
        yaml_count = len(yaml_answers)
        if yaml_count != len(answers):
            print(
                f"  WARNING: {existing_yaml.name} has {yaml_count} answers "
                f"but docx has {len(answers)} -- verify manually."
            )
        else:
            print(f"  {existing_yaml.name}  (found, {yaml_count} answers match)")
    else:
        meta_text = make_meta_yaml(len(answers), question_type)
        (out_dir / "meta.yaml").write_text(meta_text, encoding="utf-8")
        print(f"  meta.yaml  ({len(answers)} answers, type={question_type})")

    print(f"\nDone -> {out_dir}")
    if not existing_yaml:
        print("Next: open meta.yaml and set 'correct:' values and tags.")


def main():
    parser = argparse.ArgumentParser(
        description="Convert a Word exam question to exam-tool question directory format."
    )
    parser.add_argument("docx", help="Path to the .docx question file")
    parser.add_argument(
        "--out", "-o",
        help="Output directory (default: same directory as the docx file)",
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

    out_dir = Path(args.out) if args.out else docx_path.parent
    out_dir = out_dir.resolve()

    print(f"Converting: {docx_path.name}  ->  {out_dir}")
    convert(docx_path, out_dir, args.type)


if __name__ == "__main__":
    main()
