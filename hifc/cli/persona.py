from __future__ import annotations

import os
from typing import Annotated

import typer

from hifc.llm import backend_from_env
from hifc.persona import (
    ClaimNotFoundError,
    PersonaBuildError,
    build_persona,
    explain_claim,
    format_claim_explanation,
    persona_to_markdown,
)
from hifc.storage import DataRepository

app = typer.Typer(name="persona", help="Build and inspect personas.", no_args_is_help=True)


def _repo() -> DataRepository:
    return DataRepository()


@app.command("build")
def persona_build(person: Annotated[str, typer.Argument(help="person_id")]) -> None:
    backend = backend_from_env()
    model_id = getattr(backend, "model", None) or os.getenv("HIFC_LLM_BACKEND", "claude")
    try:
        result = build_persona(person, repo=_repo(), backend=backend, model_id=str(model_id))
    except PersonaBuildError as exc:
        typer.echo(f"persona build failed: {exc}", err=True)
        raise typer.Exit(1) from exc
    typer.echo(f"wrote {result.json_path}")
    typer.echo(f"wrote {result.md_path}")
    if result.persona.information_gaps:
        typer.echo("information_gaps:")
        for gap in result.persona.information_gaps:
            typer.echo(f"  - {gap}")


@app.command("show")
def persona_show(
    person: Annotated[str, typer.Argument(help="person_id")],
    version: Annotated[
        int | None, typer.Option("--version", help="persona version (default: latest)")
    ] = None,
) -> None:
    repo = _repo()
    try:
        persona = repo.read_persona(person, version=version)
    except FileNotFoundError as exc:
        typer.echo(f"persona not found: {exc}", err=True)
        raise typer.Exit(1) from exc
    sources = repo.read_sources(person)
    evidence = repo.read_evidence(person)
    typer.echo(persona_to_markdown(persona, sources, evidence))


@app.command("explain")
def persona_explain(
    person: Annotated[str, typer.Argument(help="person_id")],
    claim_id: Annotated[str, typer.Argument(help="claim_id to explain")],
    version: Annotated[int | None, typer.Option("--version")] = None,
) -> None:
    try:
        explanation = explain_claim(person, claim_id, repo=_repo(), version=version)
    except (FileNotFoundError, ClaimNotFoundError) as exc:
        typer.echo(f"explain failed: {exc}", err=True)
        raise typer.Exit(1) from exc
    typer.echo(format_claim_explanation(explanation))
