# Claude Code Instructions

## Before you start

Read `docs/architecture.md` before making any changes to the codebase.
It contains the full design: question format, data models, exporter interface,
and Moodle XML spec.

## Language and environment

- Python 3.11+
- Install dependencies with `pip install -r requirements.txt`
- All source files are UTF-8

## Project conventions

- Keep exporters self-contained in `src/exporters/`. Adding a new output format
  means adding a new file there — no changes to models, loader, or assembler.
- Do not modify `meta.yaml` files in the question bank unless explicitly asked.
  These are the answer keys and grading weights.
- Do not modify `question.md` or answer files (`a1.md`…) unless explicitly asked.
  These are the teacher's authored content.

## After making changes

- Run `python cli.py validate --exam exams/<file>.yaml` to catch broken
  question references or malformed metadata.
- Run the test suite with `pytest` before committing.

## Committing

Ask before committing. Do not commit generated files in `output/`.
