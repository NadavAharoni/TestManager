from pathlib import Path

import click
import yaml


def _load_config() -> dict:
    config_path = Path.cwd() / ".examtool.yaml"
    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


@click.group()
def cli():
    """Exam Management Tool — assemble and export exams from a question bank."""


# ---------------------------------------------------------------------------
# export
# ---------------------------------------------------------------------------

@cli.group()
def export():
    """Export an exam or question to a target format."""


@export.command("moodle")
@click.option("--exam", default=None, help="Path to exam YAML file.")
@click.option("--question", default=None, help="Path to question directory.")
@click.option("--bank", default=None, help="Path to question bank directory.")
@click.option("--output", default=None, help="Output directory.")
def export_moodle(exam, question, bank, output):
    """Export to Moodle XML."""
    from src.assembler import assemble_exam
    from src.exporters.moodle import MoodleExporter
    from src.loader import load_question

    config = _load_config()
    exporter = MoodleExporter()

    if exam and question:
        raise click.UsageError("Provide either --exam or --question, not both.")

    if exam:
        exam_path = Path(exam)
        if not exam_path.exists():
            # Try resolving against the exams directory from config
            exams_dir = config.get("exams")
            if exams_dir:
                exam_path = Path(exams_dir) / exam
        bank_path = Path(bank) if bank else None
        output_dir = Path(output or config.get("output") or (exam_path.parent / "output"))
        assembled = assemble_exam(exam_path, bank=bank_path)
        out = exporter.export_exam(assembled, output_dir)
        click.echo(f"Exported: {out}")

    elif question:
        output_dir = Path(output or config.get("output", "output"))
        q = load_question(Path(question))
        out = exporter.export_question(q, output_dir)
        click.echo(f"Exported: {out}")

    else:
        raise click.UsageError("Provide --exam or --question.")


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------

@cli.command("validate")
@click.option("--exam", default=None, help="Path to exam YAML file.")
@click.option("--question", default=None, help="Path to question directory.")
@click.option("--bank", default=None, help="Path to question bank directory.")
def validate(exam, question, bank):
    """Validate an exam definition or a single question directory."""
    from src.assembler import assemble_exam
    from src.loader import load_question

    config = _load_config()

    if exam and question:
        raise click.UsageError("Provide either --exam or --question, not both.")

    if exam:
        exam_path = Path(exam)
        if not exam_path.exists():
            exams_dir = config.get("exams")
            if exams_dir:
                exam_path = Path(exams_dir) / exam
        bank_path = Path(bank) if bank else None
        try:
            assembled = assemble_exam(exam_path, bank=bank_path)
            click.echo(
                f"OK: {assembled.id} — {len(assembled.questions)} question(s) loaded"
            )
        except Exception as exc:
            click.echo(f"ERROR: {exc}", err=True)
            raise SystemExit(1)

    elif question:
        try:
            q = load_question(Path(question))
            click.echo(
                f"OK: {q.id}  [{q.type.value}]  {len(q.answers)} answers"
            )
        except Exception as exc:
            click.echo(f"ERROR: {exc}", err=True)
            raise SystemExit(1)

    else:
        raise click.UsageError("Provide --exam or --question.")


# ---------------------------------------------------------------------------
# list-questions
# ---------------------------------------------------------------------------

@cli.command("list-questions")
@click.option("--bank", default=None, help="Path to question bank directory.")
@click.option("--tag", default=None, help="Filter by tag.")
@click.option("--type", "qtype", default=None, help="Filter by type.")
def list_questions(bank, tag, qtype):
    """List all questions in a bank, with optional filters."""
    from src.loader import load_question

    config = _load_config()
    project_root = Path(__file__).parent

    if bank:
        bank_path = Path(bank)
    elif "bank" in config:
        bank_path = Path(config["bank"])
    else:
        bank_path = project_root / "question-bank"

    if not bank_path.exists():
        click.echo(f"Bank directory not found: {bank_path}", err=True)
        raise SystemExit(1)

    count = 0
    for qdir in sorted(bank_path.iterdir()):
        if not qdir.is_dir():
            continue
        try:
            q = load_question(qdir)
        except Exception as exc:
            click.echo(f"  SKIP {qdir.name}: {exc}", err=True)
            continue

        if tag and tag not in q.tags:
            continue
        if qtype and q.type.value != qtype:
            continue

        click.echo(f"{q.id:<40} [{q.type.value}]  tags: {', '.join(q.tags)}")
        count += 1

    click.echo(f"\n{count} question(s) found.")


if __name__ == "__main__":
    cli()
