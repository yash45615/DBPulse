"""Command-line interface for DBPulse."""

import os

import typer
from rich.console import Console
from rich.table import Table
from sqlalchemy.exc import SQLAlchemyError

from dbpulse import __version__
from dbpulse.analytics import latency_summary
from dbpulse.config import load_config
from dbpulse.db import (
    check_database_connection,
    create_database_engine,
    initialize_schema,
)
from dbpulse.history import (
    get_run_measurements,
    list_runs,
    save_workload_result,
)
from dbpulse.manifest import build_manifest, write_manifest
from dbpulse.profiles import get_profile, list_profiles
from dbpulse.regression import compare_latency_values
from dbpulse.reports import build_comparison_report, write_json_report
from dbpulse.workloads import run_workload, seed_dataset

app = typer.Typer(
    name="dbpulse",
    help="Database performance benchmarking and workload regression lab.",
    no_args_is_help=True,
)
console = Console()


def resolve_database_url(config_path: str) -> str:
    """Resolve the database URL, allowing an environment override."""
    settings = load_config(config_path)
    return os.environ.get(
        "DBPULSE_DATABASE_URL",
        settings.database.url,
    )


@app.command()
def version() -> None:
    """Display the installed DBPulse version."""
    console.print(f"DBPulse {__version__}")


@app.command("config-check")
def config_check(
    config: str = typer.Option(
        "config/dbpulse.toml",
        "--config",
        help="Path to the TOML configuration file.",
    ),
) -> None:
    """Validate configuration and display its settings."""
    try:
        settings = load_config(config)
    except (OSError, ValueError, TypeError) as exc:
        console.print(f"[red]Configuration error:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    table = Table(title="DBPulse Configuration")
    table.add_column("Setting")
    table.add_column("Value")

    table.add_row("Environment", settings.app.environment)
    table.add_row("Database URL", settings.database.url)
    table.add_row("Workload", settings.benchmark.default_workload)
    table.add_row("Iterations", str(settings.benchmark.iterations))
    table.add_row(
        "Warm-up iterations",
        str(settings.benchmark.warmup_iterations),
    )
    table.add_row("Concurrency", str(settings.benchmark.concurrency))
    table.add_row(
        "Regression threshold",
        f"{settings.regression.latency_threshold_percent}%",
    )
    table.add_row("Report directory", settings.reports.output_dir)

    console.print(table)
    console.print("[green]Configuration is valid.[/green]")


@app.command("db-health")
def db_health(
    config: str = typer.Option(
        "config/dbpulse.toml",
        "--config",
        help="Path to the TOML configuration file.",
    ),
) -> None:
    """Check whether the configured database is reachable."""
    engine = None

    try:
        database_url = resolve_database_url(config)
        engine = create_database_engine(database_url)

        if not check_database_connection(engine):
            console.print("[red]Database health check failed.[/red]")
            raise typer.Exit(code=1)

        console.print("[green]Database connection successful.[/green]")
        console.print("SELECT 1 returned the expected result.")

    except (OSError, ValueError, SQLAlchemyError) as exc:
        console.print(f"[red]Database connection failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    finally:
        if engine is not None:
            engine.dispose()


@app.command("init-db")
def init_db(
    config: str = typer.Option(
        "config/dbpulse.toml",
        "--config",
        help="Path to the TOML configuration file.",
    ),
) -> None:
    """Create tables and apply supported schema migrations."""
    engine = None

    try:
        database_url = resolve_database_url(config)
        engine = create_database_engine(database_url)
        initialize_schema(engine)

        console.print("[green]Database schema initialized.[/green]")
        console.print(
            "Tables: benchmark_runs, workload_records, benchmark_measurements"
        )
        console.print("Existing benchmark metadata migration checked.")

    except (OSError, ValueError, SQLAlchemyError) as exc:
        console.print(f"[red]Schema initialization failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    finally:
        if engine is not None:
            engine.dispose()


@app.command("seed-data")
def seed_data(
    dataset_size: int = typer.Option(
        1000,
        "--dataset-size",
        min=1,
        help="Minimum number of synthetic records to create.",
    ),
    config: str = typer.Option(
        "config/dbpulse.toml",
        "--config",
        help="Path to the TOML configuration file.",
    ),
) -> None:
    """Prepare synthetic records for benchmark workloads."""
    engine = None

    try:
        database_url = resolve_database_url(config)
        engine = create_database_engine(database_url)
        initialize_schema(engine)
        total = seed_dataset(engine, dataset_size)

        console.print("[green]Benchmark dataset is ready.[/green]")
        console.print(f"Records available: {total}")

    except (OSError, ValueError, SQLAlchemyError) as exc:
        console.print(f"[red]Dataset preparation failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    finally:
        if engine is not None:
            engine.dispose()


@app.command("benchmark-workload")
def benchmark_workload(
    workload: str = typer.Option(
        "read",
        "--workload",
        help="Workload type: read, write, or mixed.",
    ),
    iterations: int = typer.Option(
        100,
        "--iterations",
        min=1,
        help="Number of database operations to execute.",
    ),
    dataset_size: int = typer.Option(
        1000,
        "--dataset-size",
        min=1,
        help="Minimum number of synthetic records to prepare.",
    ),
    name: str = typer.Option(
        "manual-benchmark",
        "--name",
        help="Name to identify this benchmark run.",
    ),
    profile: str = typer.Option(
        "custom",
        "--profile",
        help=("Metadata profile label: custom, smoke, standard, or repeatable."),
    ),
    config: str = typer.Option(
        "config/dbpulse.toml",
        "--config",
        help="Path to the TOML configuration file.",
    ),
) -> None:
    """Execute, measure, and save a database workload with metadata."""
    engine = None

    try:
        database_url = resolve_database_url(config)
        engine = create_database_engine(database_url)
        initialize_schema(engine)
        seed_dataset(engine, dataset_size)

        # Validate a named profile and use it as a label for this run.
        # Explicit CLI iteration and dataset-size values remain authoritative.
        if profile != "custom":
            get_profile(profile)

        result = run_workload(engine, workload, iterations)

        run_metadata = build_manifest(
            profile_name=profile,
            workload=result.workload,
            database_url=database_url,
            iterations=len(result.latencies_ms),
            dataset_size=dataset_size,
        )

        run_id = save_workload_result(
            engine,
            name,
            result,
            metadata=run_metadata,
        )
        summary = latency_summary(result.latencies_ms)

        table = Table(title=f"DBPulse {result.workload.title()} Workload")
        table.add_column("Metric")
        table.add_column("Result", justify="right")

        table.add_row("Run ID", str(run_id))
        table.add_row("Run name", name)
        table.add_row("Profile", profile)
        table.add_row("Operations", str(result.iterations))
        table.add_row("Reads", str(result.reads))
        table.add_row("Writes", str(result.writes))
        table.add_row("Mean latency", f"{summary['mean_ms']:.3f} ms")
        table.add_row("Minimum latency", f"{summary['min_ms']:.3f} ms")
        table.add_row("P50 latency", f"{summary['p50_ms']:.3f} ms")
        table.add_row("P95 latency", f"{summary['p95_ms']:.3f} ms")
        table.add_row("P99 latency", f"{summary['p99_ms']:.3f} ms")
        table.add_row("Maximum latency", f"{summary['max_ms']:.3f} ms")
        table.add_row(
            "Total measured duration",
            f"{result.total_duration_ms:.3f} ms",
        )

        console.print(table)
        console.print("[green]Benchmark run and metadata saved successfully.[/green]")

    except (OSError, ValueError, TypeError, SQLAlchemyError) as exc:
        console.print(f"[red]Workload execution failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    finally:
        if engine is not None:
            engine.dispose()


@app.command("history")
def show_history(
    limit: int = typer.Option(
        20,
        "--limit",
        min=1,
        help="Maximum number of recent runs to display.",
    ),
    config: str = typer.Option(
        "config/dbpulse.toml",
        "--config",
        help="Path to the TOML configuration file.",
    ),
) -> None:
    """List recent benchmark runs."""
    engine = None

    try:
        engine = create_database_engine(resolve_database_url(config))
        runs = list_runs(engine, limit=limit)

        if not runs:
            console.print("No benchmark runs found.")
            return

        table = Table(title="DBPulse Benchmark History")
        table.add_column("ID")
        table.add_column("Name")
        table.add_column("Workload")
        table.add_column("Status")
        table.add_column("Created at")

        for run in runs:
            created_at = run.created_at.isoformat() if run.created_at else "Unknown"
            table.add_row(
                str(run.id),
                run.name,
                run.workload,
                run.status,
                created_at,
            )

        console.print(table)

    except (OSError, ValueError, SQLAlchemyError) as exc:
        console.print(f"[red]History lookup failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    finally:
        if engine is not None:
            engine.dispose()


@app.command("show-run")
def show_run(
    run_id: int = typer.Argument(..., min=1),
    config: str = typer.Option(
        "config/dbpulse.toml",
        "--config",
        help="Path to the TOML configuration file.",
    ),
) -> None:
    """Display latency statistics and metadata for one saved run."""
    engine = None

    try:
        engine = create_database_engine(resolve_database_url(config))
        retrieved = get_run_measurements(engine, run_id)

        if retrieved is None:
            console.print(f"[red]Benchmark run {run_id} was not found.[/red]")
            raise typer.Exit(code=1)

        run, measurements = retrieved

        table = Table(title=f"Benchmark Run {run.id}: {run.name}")
        table.add_column("Metric")
        table.add_column("Value", justify="right")

        table.add_row("Workload", run.workload)
        table.add_row("Status", run.status)
        table.add_row("Created at", str(run.created_at))

        metadata = run.metadata_json or {}
        profile_info = metadata.get("profile", {})
        workload_info = metadata.get("workload", {})
        environment_info = metadata.get("environment", {})

        table.add_row(
            "Profile",
            str(profile_info.get("name", "Not recorded")),
        )
        table.add_row(
            "Configured iterations",
            str(workload_info.get("iterations", "Not recorded")),
        )
        table.add_row(
            "Dataset size",
            str(workload_info.get("dataset_size", "Not recorded")),
        )
        table.add_row(
            "Python version",
            str(environment_info.get("python_version", "Not recorded")),
        )
        table.add_row(
            "Database backend",
            str(environment_info.get("database_backend", "Not recorded")),
        )

        if not measurements:
            console.print(table)
            console.print("This run has no saved measurements.")
            return

        latencies = tuple(item.latency_ms for item in measurements)
        summary = latency_summary(latencies)

        table.add_row("Measurements", str(len(measurements)))
        table.add_row(
            "Reads",
            str(sum(item.operation_type == "read" for item in measurements)),
        )
        table.add_row(
            "Writes",
            str(sum(item.operation_type == "write" for item in measurements)),
        )

        for label, key in (
            ("Mean latency", "mean_ms"),
            ("Minimum latency", "min_ms"),
            ("P50 latency", "p50_ms"),
            ("P95 latency", "p95_ms"),
            ("P99 latency", "p99_ms"),
            ("Maximum latency", "max_ms"),
        ):
            table.add_row(label, f"{summary[key]:.3f} ms")

        console.print(table)

    except (OSError, ValueError, SQLAlchemyError) as exc:
        console.print(f"[red]Run lookup failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    finally:
        if engine is not None:
            engine.dispose()


@app.command("compare")
def compare_runs_command(
    baseline_id: int = typer.Argument(..., min=1),
    candidate_id: int = typer.Argument(..., min=1),
    threshold: float = typer.Option(
        10.0,
        "--threshold",
        min=0.0,
        help="Percentage increase that counts as a regression.",
    ),
    config: str = typer.Option(
        "config/dbpulse.toml",
        "--config",
        help="Path to the TOML configuration file.",
    ),
) -> None:
    """Compare two saved benchmark runs and detect regressions."""
    engine = None

    try:
        engine = create_database_engine(resolve_database_url(config))

        baseline_data = get_run_measurements(engine, baseline_id)
        candidate_data = get_run_measurements(engine, candidate_id)

        if baseline_data is None:
            console.print(f"[red]Baseline run {baseline_id} was not found.[/red]")
            raise typer.Exit(code=1)

        if candidate_data is None:
            console.print(f"[red]Candidate run {candidate_id} was not found.[/red]")
            raise typer.Exit(code=1)

        baseline_run, baseline_measurements = baseline_data
        candidate_run, candidate_measurements = candidate_data

        if baseline_run.workload != candidate_run.workload:
            console.print("[red]Cannot compare runs with different workloads.[/red]")
            raise typer.Exit(code=1)

        if not baseline_measurements or not candidate_measurements:
            console.print("[red]Both runs must contain measurements.[/red]")
            raise typer.Exit(code=1)

        baseline_latencies = tuple(item.latency_ms for item in baseline_measurements)
        candidate_latencies = tuple(item.latency_ms for item in candidate_measurements)

        report = compare_latency_values(
            baseline_id,
            candidate_id,
            baseline_latencies,
            candidate_latencies,
            threshold_percent=threshold,
        )

        table = Table(title="DBPulse Regression Report")
        table.add_column("Metric")
        table.add_column("Baseline", justify="right")
        table.add_column("Candidate", justify="right")
        table.add_column("Change", justify="right")
        table.add_column("Result")

        for metric in report.metrics:
            if metric.regressed:
                status = "[red]REGRESSION[/red]"
            elif metric.change_percent < 0:
                status = "[green]IMPROVED[/green]"
            else:
                status = "[green]WITHIN THRESHOLD[/green]"

            change_text = (
                "+infinity%"
                if metric.change_percent == float("inf")
                else f"{metric.change_percent:+.2f}%"
            )

            table.add_row(
                metric.metric.upper(),
                f"{metric.baseline_ms:.3f} ms",
                f"{metric.candidate_ms:.3f} ms",
                change_text,
                status,
            )

        console.print(table)
        console.print(f"Baseline run: {baseline_run.name} (ID {baseline_id})")
        console.print(f"Candidate run: {candidate_run.name} (ID {candidate_id})")
        console.print(f"Regression threshold: {threshold:.2f}%")

        if report.has_regression:
            console.print("[red]Performance regression detected.[/red]")
            raise typer.Exit(code=2)

        console.print("[green]No latency regression detected.[/green]")

    except (OSError, ValueError, SQLAlchemyError) as exc:
        console.print(f"[red]Comparison failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    finally:
        if engine is not None:
            engine.dispose()


@app.command("report")
def export_report(
    baseline_id: int = typer.Argument(..., min=1),
    candidate_id: int = typer.Argument(..., min=1),
    threshold: float = typer.Option(
        10.0,
        "--threshold",
        min=0.0,
        help="Percentage increase that counts as a regression.",
    ),
    output: str = typer.Option(
        "reports/comparison.json",
        "--output",
        help="Path where the JSON report will be saved.",
    ),
    config: str = typer.Option(
        "config/dbpulse.toml",
        "--config",
        help="Path to the TOML configuration file.",
    ),
) -> None:
    """Export a JSON report comparing two saved benchmark runs."""
    engine = None

    try:
        engine = create_database_engine(resolve_database_url(config))

        baseline_data = get_run_measurements(engine, baseline_id)
        candidate_data = get_run_measurements(engine, candidate_id)

        if baseline_data is None:
            console.print(f"[red]Baseline run {baseline_id} not found.[/red]")
            raise typer.Exit(code=1)

        if candidate_data is None:
            console.print(f"[red]Candidate run {candidate_id} not found.[/red]")
            raise typer.Exit(code=1)

        baseline_run, baseline_measurements = baseline_data
        candidate_run, candidate_measurements = candidate_data

        if baseline_run.workload != candidate_run.workload:
            console.print("[red]Cannot report on different workload types.[/red]")
            raise typer.Exit(code=1)

        if not baseline_measurements or not candidate_measurements:
            console.print("[red]Both runs must contain measurements.[/red]")
            raise typer.Exit(code=1)

        report = build_comparison_report(
            baseline_run_id=baseline_id,
            candidate_run_id=candidate_id,
            baseline_name=baseline_run.name,
            candidate_name=candidate_run.name,
            workload=baseline_run.workload,
            baseline_latencies=tuple(item.latency_ms for item in baseline_measurements),
            candidate_latencies=tuple(
                item.latency_ms for item in candidate_measurements
            ),
            threshold_percent=threshold,
        )

        saved_path = write_json_report(report, output)

        console.print("[green]Comparison report exported.[/green]")
        console.print(f"File: {saved_path.resolve()}")
        console.print(f"Regression detected: {report['comparison']['has_regression']}")

    except (OSError, ValueError, SQLAlchemyError) as exc:
        console.print(f"[red]Report generation failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    finally:
        if engine is not None:
            engine.dispose()


@app.command("profiles")
def show_profiles() -> None:
    """List available benchmark profiles."""
    table = Table(title="DBPulse Benchmark Profiles")
    table.add_column("Profile")
    table.add_column("Iterations", justify="right")
    table.add_column("Dataset Size", justify="right")
    table.add_column("Description")

    for profile in list_profiles():
        table.add_row(
            str(profile["name"]),
            str(profile["iterations"]),
            str(profile["dataset_size"]),
            str(profile["description"]),
        )

    console.print(table)


@app.command("manifest")
def export_manifest(
    profile: str = typer.Option(
        "standard",
        "--profile",
        help="Profile name: smoke, standard, or repeatable.",
    ),
    workload: str = typer.Option(
        "read",
        "--workload",
        help="Workload type: read, write, or mixed.",
    ),
    iterations: int | None = typer.Option(
        None,
        "--iterations",
        min=1,
        help="Override the profile's iteration count.",
    ),
    dataset_size: int | None = typer.Option(
        None,
        "--dataset-size",
        min=1,
        help="Override the profile's dataset size.",
    ),
    output: str = typer.Option(
        "reports/manifests/benchmark-manifest.json",
        "--output",
        help="Output path for the JSON manifest.",
    ),
    config: str = typer.Option(
        "config/dbpulse.toml",
        "--config",
        help="Path to the TOML configuration file.",
    ),
) -> None:
    """Export the environment and settings for a planned benchmark."""
    try:
        database_url = resolve_database_url(config)
        manifest = build_manifest(
            profile_name=profile,
            workload=workload,
            database_url=database_url,
            iterations=iterations,
            dataset_size=dataset_size,
        )
        saved_path = write_manifest(manifest, output)

        console.print("[green]Benchmark manifest exported.[/green]")
        console.print(f"File: {saved_path.resolve()}")

    except (OSError, ValueError, TypeError) as exc:
        console.print(f"[red]Manifest generation failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc


if __name__ == "__main__":
    app()
