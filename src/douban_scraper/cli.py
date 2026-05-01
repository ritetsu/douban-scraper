"""Douban Scraper CLI — export user collection data via Douban APIs."""

from __future__ import annotations

import csv
import json
import os
import time
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table

from douban_scraper.frodo import API_KEY, DEFAULT_USER_AGENT, HMAC_SECRET, DoubanFrodoClient
from douban_scraper.rexxar import DoubanRexxarClient
from douban_scraper.state import StateManager

FILE_NAMES = {"movie": "movies", "book": "books", "music": "music", "broadcast": "broadcasts"}

app = typer.Typer(no_args_is_help=True)
console = Console()


@app.callback()
def main() -> None:
    """Douban Scraper — export user collection data from Douban."""


@app.command()
def export(
    user: str = typer.Option(..., "--user", "-u", help="Douban user ID"),
    types: str = typer.Option(
        "movie,book,music", "--types", "-t", help="Comma-separated content types"
    ),
    status: str = typer.Option(
        "done", "--status", "-s", help="Comma-separated statuses (done, doing, mark, or 'all')"
    ),
    output: str = typer.Option(
        "./output", "--output", "-o", help="Output directory"
    ),
    cookie: Optional[str] = typer.Option(
        None, "--cookie", "-c", help="Douban ck cookie (required for broadcasts)"
    ),
    delay: float = typer.Option(
        1.5, "--delay", "-d", help="Delay between requests in seconds"
    ),
    max_items: int = typer.Option(
        0, "--max-items", "-m", help="Max items per type/status (0 = unlimited)"
    ),
    api_key: Optional[str] = typer.Option(
        None, "--api-key", help="Douban Frodo API key"
    ),
    api_secret: Optional[str] = typer.Option(
        None, "--api-secret", help="Douban Frodo HMAC secret"
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Overwrite existing output files"
    ),
) -> None:
    """Export Douban user collection data (movies, books, music, broadcasts)."""
    start_time = time.monotonic()

    resolved_api_key = api_key or API_KEY
    resolved_api_secret = (
        api_secret.encode() if api_secret else HMAC_SECRET
    )

    type_list = [t.strip() for t in types.split(",") if t.strip()]
    VALID_TYPES = {"movie", "book", "music", "broadcast"}
    invalid_types = [t for t in type_list if t not in VALID_TYPES]
    if invalid_types:
        console.print(f"[red]Error:[/red] Invalid types: {', '.join(invalid_types)}. Valid: {', '.join(sorted(VALID_TYPES))}")
        raise typer.Exit(code=1)
    status_str = status.strip().lower()
    if status_str == "all":
        status_list = ["done", "doing", "mark"]
    else:
        status_list = [s.strip() for s in status_str.split(",") if s.strip()]
        VALID_STATUSES = {"done", "doing", "mark"}
        invalid_statuses = [s for s in status_list if s not in VALID_STATUSES]
        if invalid_statuses:
            console.print(f"[red]Error:[/red] Invalid statuses: {', '.join(invalid_statuses)}. Valid: {', '.join(sorted(VALID_STATUSES))}, or 'all'")
            raise typer.Exit(code=1)

    output_dir = Path(output)
    os.makedirs(output_dir, exist_ok=True)

    if not force:
        existing = [f for f in output_dir.glob("*.json") if f.name != ".progress.json"]
        if existing:
            names = ", ".join(f.name for f in existing)
            console.print(
                f"[red]Error:[/red] Output files already exist: {names}\n"
                "Use --force to overwrite."
            )
            raise typer.Exit(code=1)
    else:
        for f in output_dir.glob("*.json"):
            f.unlink()

    client = DoubanFrodoClient(
        api_key=resolved_api_key,
        api_secret=resolved_api_secret,
        user_agent=DEFAULT_USER_AGENT,
    )
    client._rate_limiter.delay = delay

    console.print(f"Validating user [cyan]{user}[/cyan]...")
    if not client.validate_user(user):
        console.print(f"[red]Error:[/red] Could not validate user '{user}'. Check the user ID.")
        raise typer.Exit(code=1)
    console.print("[green]User validated.[/green]")

    state = StateManager(output_dir)
    results: dict[str, int] = {}
    all_failures: list[dict] = []

    tasks: list[tuple[str, str]] = []
    for type_ in type_list:
        if type_ == "broadcast":
            continue
        for stat in status_list:
            tasks.append((type_, stat))

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        for type_, stat in tasks:
            key = f"{type_}_{stat}"
            file_path = output_dir / f"{FILE_NAMES.get(type_, type_ + 's')}.json"

            if not force and state.is_completed(key):
                console.print(f"  [dim]Skipping {key} (already completed)[/dim]")
                continue

            task_id = progress.add_task(f"{type_}/{stat}", total=None)
            start_offset = state.get_offset(key)
            client.failures = []

            def _make_callback(k: str, tid: int):
                def cb(t: str, s: str, offset: int, total: int | None) -> None:
                    if total:
                        progress.update(tid, completed=offset, total=total)
                    p = state.load()
                    p[k] = {"start": offset, "completed": False}
                    state.save(p)
                return cb

            try:
                items = client.export_all(
                    user_id=user,
                    type_=type_,
                    status=stat,
                    progress_callback=_make_callback(key, task_id),
                    max_items=max_items,
                    start_offset=start_offset,
                )
            except Exception as exc:
                console.print(f"  [red]Error exporting {key}: {exc}[/red]")
                all_failures.append({"key": key, "error": str(exc)})
                continue

            if max_items > 0 and len(items) > max_items:
                items = items[:max_items]

            existing_items: list[dict] = []
            if file_path.exists():
                with open(file_path, "r", encoding="utf-8") as f:
                    existing_items = json.load(f)

            existing_items.extend(items)
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(existing_items, f, ensure_ascii=False, indent=2)

            state.mark_completed(key)
            results[key] = len(items)
            all_failures.extend(client.failures)
            progress.update(task_id, total=100, completed=100)

    if "broadcast" in type_list:
        if not cookie:
            console.print(
                "[yellow]Skipping broadcasts:[/yellow] --cookie is required for broadcast export."
            )
        else:
            console.print("Exporting [cyan]broadcasts[/cyan] via Rexxar API...")
            rexxar = DoubanRexxarClient(ck_cookie=cookie)
            try:
                broadcasts = rexxar.export_all(user_id=user, max_items=max_items)
                broadcast_path = output_dir / "broadcasts.json"
                with open(broadcast_path, "w", encoding="utf-8") as f:
                    json.dump(broadcasts, f, ensure_ascii=False, indent=2)
                results["broadcast"] = len(broadcasts)
                console.print(f"  [green]Exported {len(broadcasts)} broadcasts.[/green]")
            except Exception as exc:
                console.print(f"  [red]Error exporting broadcasts: {exc}[/red]")
                all_failures.append({"key": "broadcast", "error": str(exc)})

    retry_failures = [f for f in all_failures if "key" in f]
    for retry_round in range(3):
        if not retry_failures:
            break
        console.print(
            f"\n[yellow]Retry round {retry_round + 1}/3[/yellow] — "
            f"{len(retry_failures)} failed tasks"
        )
        still_failing: list[dict] = []
        for fail in retry_failures:
            key = fail["key"]
            parts = key.split("_", 1)
            if len(parts) != 2:
                still_failing.append(fail)
                continue
            type_, stat = parts
            console.print(f"  Retrying {key}...")
            client.failures = []
            try:
                items = client.export_all(
                    user_id=user,
                    type_=type_,
                    status=stat,
                    max_items=max_items,
                    start_offset=0,
                )
                file_path = output_dir / f"{FILE_NAMES.get(type_, type_ + 's')}.json"
                with open(file_path, "r", encoding="utf-8") as f:
                    existing_items = json.load(f)
                existing_items.extend(items)
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(existing_items, f, ensure_ascii=False, indent=2)
                state.mark_completed(key)
                results[key] = results.get(key, 0) + len(items)
                console.print(f"  [green]Retry succeeded for {key}:[/green] {len(items)} items")
            except Exception as exc:
                console.print(f"  [red]Retry failed for {key}: {exc}[/red]")
                still_failing.append({"key": key, "error": str(exc)})
            all_failures.extend(client.failures)
        retry_failures = still_failing

    elapsed = time.monotonic() - start_time
    console.print()

    summary_table = Table(title="Export Summary")
    summary_table.add_column("Type/Status", style="cyan")
    summary_table.add_column("Items", justify="right", style="green")

    for key, count in results.items():
        summary_table.add_row(key, str(count))

    total_items = sum(results.values())
    summary_table.add_row("[bold]Total[/bold]", f"[bold]{total_items}[/bold]")
    console.print(summary_table)

    if all_failures:
        console.print(f"\n[red]Failures: {len(all_failures)}[/red]")
        for fail in all_failures[:10]:
            console.print(f"  • {fail.get('key', 'unknown')}: {fail.get('error', 'unknown')}")

    console.print(f"\nTime: [cyan]{elapsed:.1f}s[/cyan]")
    console.print(f"Output: [cyan]{output_dir}[/cyan]")

    if all_failures:
        raise typer.Exit(code=2)


CSV_COLUMNS = ["title", "type", "my_rating", "comment", "create_time", "year", "genres", "douban_rating", "card_subtitle", "url", "tags"]


@app.command(name="to-csv")
def to_csv(
    input_dir: str = typer.Option(..., "--input", "-i", help="Directory containing JSON output files"),
) -> None:
    """Convert exported JSON files to a single CSV."""
    input_path = Path(input_dir)
    if not input_path.is_dir():
        console.print(f"[red]Error:[/red] Directory not found: {input_dir}")
        raise typer.Exit(code=1)

    all_items: list[dict] = []
    for filename in ["movies.json", "books.json"]:
        filepath = input_path / filename
        if not filepath.exists():
            console.print(f"[yellow]Skipping:[/yellow] {filename} not found")
            continue
        with open(filepath, "r", encoding="utf-8") as f:
            items = json.load(f)
        if not items:
            console.print(f"[dim]Skipping {filename} (0 items)[/dim]")
            continue
        all_items.extend(items)

    if not all_items:
        console.print("[red]Error:[/red] No data found. Run `douban-scraper export` first.")
        raise typer.Exit(code=1)

    rows: list[dict] = []
    for item in all_items:
        subject = item.get("subject", {})
        rating = item.get("rating") or {}
        row = {
            "title": subject.get("title", ""),
            "type": subject.get("type", ""),
            "my_rating": rating.get("value", ""),
            "comment": item.get("comment", ""),
            "create_time": item.get("create_time", ""),
            "year": subject.get("year", "") or "",
            "genres": ", ".join(subject.get("genres", [])),
            "douban_rating": subject.get("rating", {}).get("value", ""),
            "card_subtitle": subject.get("card_subtitle", ""),
            "url": subject.get("url", ""),
            "tags": ", ".join(item.get("tags", [])),
        }
        if row["my_rating"] != "":
            row["my_rating"] = str(row["my_rating"])
        if row["douban_rating"] != "":
            row["douban_rating"] = str(row["douban_rating"])
        rows.append(row)

    rows.sort(key=lambda r: r["create_time"], reverse=True)

    output_path = input_path / "douban_export.csv"
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    console.print(f"Wrote [green]{len(rows)}[/green] rows to [cyan]{output_path}[/cyan]")


if __name__ == "__main__":
    app()
