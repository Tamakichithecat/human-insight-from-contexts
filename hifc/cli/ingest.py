from __future__ import annotations

import sys
from datetime import date
from pathlib import Path
from typing import Annotated

import typer

from hifc.ingest import (
    IngestError,
    YoutubeTranscriptUnavailable,
    build_source_from_file,
    build_source_from_paste,
    build_source_from_url,
    build_source_from_youtube,
    load_csv_sources,
)
from hifc.schemas.source import AuthorPerspective, SourceType
from hifc.storage import DataRepository

app = typer.Typer(name="ingest", help="Ingest source documents for a person.", no_args_is_help=True)


def _repo() -> DataRepository:
    return DataRepository()


def _parse_date(value: str | None) -> date | None:
    if value is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        typer.echo(f"invalid --date {value!r}, expected YYYY-MM-DD", err=True)
        raise typer.Exit(1) from exc


@app.command("url")
def ingest_url(
    url: Annotated[str, typer.Argument(help="Article/blog URL to fetch and extract.")],
    person: Annotated[str, typer.Option("--person", help="person_id")],
    source_type: Annotated[SourceType, typer.Option("--type", help="source_type")],
    perspective: Annotated[AuthorPerspective, typer.Option("--perspective")] = "third_party",
    published: Annotated[
        str | None, typer.Option("--date", help="published date (YYYY-MM-DD)")
    ] = None,
) -> None:
    try:
        source = build_source_from_url(
            url,
            person_id=person,
            source_type=source_type,
            author_perspective=perspective,
            published_at=_parse_date(published),
        )
    except IngestError as exc:
        typer.echo(f"ingest failed: {exc}", err=True)
        raise typer.Exit(1) from exc
    path = _repo().write_source(source)
    typer.echo(f"wrote {path} (source_id={source.source_id})")


@app.command("file")
def ingest_file(
    path: Annotated[Path, typer.Argument(help=".txt/.md/.pdf file to ingest.")],
    person: Annotated[str, typer.Option("--person")],
    source_type: Annotated[SourceType, typer.Option("--type")],
    perspective: Annotated[AuthorPerspective, typer.Option("--perspective")] = "third_party",
    published: Annotated[str | None, typer.Option("--date")] = None,
) -> None:
    try:
        source = build_source_from_file(
            path,
            person_id=person,
            source_type=source_type,
            author_perspective=perspective,
            published_at=_parse_date(published),
        )
    except IngestError as exc:
        typer.echo(f"ingest failed: {exc}", err=True)
        raise typer.Exit(1) from exc
    written = _repo().write_source(source)
    typer.echo(f"wrote {written} (source_id={source.source_id})")


_CSV_HELP = "CSV with columns: text,date,source_type,origin,author_perspective,title."


@app.command("csv")
def ingest_csv(
    path: Annotated[Path, typer.Argument(help=_CSV_HELP)],
    person: Annotated[str, typer.Option("--person")],
    default_type: Annotated[
        SourceType | None, typer.Option("--type", help="default source_type for rows that omit it")
    ] = None,
    default_perspective: Annotated[
        AuthorPerspective | None,
        typer.Option("--perspective", help="default author_perspective for rows that omit it"),
    ] = None,
) -> None:
    try:
        sources = load_csv_sources(
            path,
            person_id=person,
            default_source_type=default_type,
            default_author_perspective=default_perspective,
        )
    except IngestError as exc:
        typer.echo(f"ingest failed: {exc}", err=True)
        raise typer.Exit(1) from exc
    repo = _repo()
    for source in sources:
        written = repo.write_source(source)
        typer.echo(f"wrote {written} (source_id={source.source_id})")
    typer.echo(f"ingested {len(sources)} row(s) from {path}")


@app.command("paste")
def ingest_paste(
    person: Annotated[str, typer.Option("--person")],
    source_type: Annotated[SourceType, typer.Option("--type")],
    perspective: Annotated[AuthorPerspective, typer.Option("--perspective")],
    published: Annotated[str | None, typer.Option("--date")] = None,
    title: Annotated[str | None, typer.Option("--title")] = None,
    text: Annotated[
        str | None,
        typer.Option("--text", help="text content; omit to read from stdin (YouTube fallback)"),
    ] = None,
) -> None:
    raw_text = text if text is not None else sys.stdin.read()
    if not raw_text.strip():
        typer.echo("no text provided (pass --text or pipe content via stdin)", err=True)
        raise typer.Exit(1)
    try:
        source = build_source_from_paste(
            person_id=person,
            raw_text=raw_text,
            source_type=source_type,
            author_perspective=perspective,
            title=title,
            published_at=_parse_date(published),
        )
    except ValueError as exc:
        typer.echo(f"ingest failed: {exc}", err=True)
        raise typer.Exit(1) from exc
    written = _repo().write_source(source)
    typer.echo(f"wrote {written} (source_id={source.source_id})")


@app.command("youtube")
def ingest_youtube(
    url: Annotated[str, typer.Argument(help="YouTube video URL or video id.")],
    person: Annotated[str, typer.Option("--person")],
    perspective: Annotated[AuthorPerspective, typer.Option("--perspective")] = "first_person",
    published: Annotated[str | None, typer.Option("--date")] = None,
) -> None:
    try:
        source = build_source_from_youtube(
            url,
            person_id=person,
            author_perspective=perspective,
            published_at=_parse_date(published),
        )
    except YoutubeTranscriptUnavailable as exc:
        typer.echo(f"YouTube transcript unavailable: {exc}", err=True)
        typer.echo(
            "fallback: copy the transcript manually and run "
            "`hifc ingest paste --type video_transcript --person ... --text ...`",
            err=True,
        )
        raise typer.Exit(1) from exc
    written = _repo().write_source(source)
    typer.echo(f"wrote {written} (source_id={source.source_id})")
