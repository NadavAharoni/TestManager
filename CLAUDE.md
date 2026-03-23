# Claude Code Instructions

## Before you start

Read `docs/architecture.md` before making any changes to the codebase.
It contains the full design: question format, data models, exporter interface,
Moodle XML spec, and the two-repo setup.

## Two-repo setup

This is the **public tool repo** (`exam-tool`). It contains only the code.
The actual question bank and exam definitions live in a separate **private repo**
and are never committed here.

When working with real questions, the private repo is pointed to via
`--bank`, `--exams`, or a local `.examtool.yaml` config file (see architecture).
Do not create or assume a `question-bank/` directory exists in this repo —
use the `example-questions/` directory for development and testing instead.

## Language and environment

- Python 3.11+
- Install dependencies with `pip install -r requirements.txt`
- All source files are UTF-8

## Project conventions

- Keep exporters self-contained in `src/exporters/`. Adding a new output format
  means adding a new file there — no changes to models, loader, or assembler.
- Do not modify files in `example-questions/` unless explicitly asked.
- Never commit real question content, answer keys, or exam definitions here.
  Those belong in the private questions repo.

## After making changes

- Run `python cli.py validate --bank example-questions/ --exam example-questions/exams/demo.yaml`
  to catch broken question references or malformed metadata.
- Run the test suite with `pytest` before committing.

## Committing

Ask before committing. Do not commit generated files in `output/`.
Do not commit any `.examtool.yaml` config file — it is gitignored.
