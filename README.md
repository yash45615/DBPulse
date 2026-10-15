# DBPulse — Database Performance Benchmarking & Regression Detection

**DBPulse** is a Python-based database performance benchmarking toolkit designed to execute repeatable workloads, analyze query-operation latency, track benchmark history, and detect potential performance regressions.

Built with Python, SQLAlchemy, and PostgreSQL support, DBPulse provides structured benchmark measurements, percentile-based latency analysis, JSON reports, and reproducibility manifests to help developers understand and compare database performance.

## Key Features

- **Workload benchmarking:** Execute read, write, and mixed database workloads.
- **Latency analytics:** Calculate mean, minimum, maximum, P50, P95, and P99 latency.
- **Regression detection:** Compare baseline and candidate benchmark runs against a configurable threshold.
- **Benchmark history:** Persist runs and individual operation measurements for later analysis.
- **Reproducibility manifests:** Record workload settings and environment information.
- **JSON reports:** Export structured comparison reports for further analysis or automation.
- **Benchmark profiles:** Use predefined smoke, standard, and repeatable configurations.
- **Database health checks:** Verify connectivity and initialize the required schema.
- **Automated testing:** Validate analytics, configuration, database operations, history, reports, and workload execution.

## Technology Stack

| Technology | Purpose |
|---|---|
| Python 3.11+ | Core implementation |
| SQLAlchemy | Database connectivity and ORM |
| PostgreSQL | Relational database benchmarking |
| SQLite | Lightweight local development and testing |
| Typer | Command-line interface |
| Rich | Terminal output and benchmark tables |
| Pytest | Automated testing |
| Ruff | Linting and code formatting |

## Architecture

```text
                 DBPulse CLI
                      |
          Configuration & Profiles
                      |
              Workload Runner
               /     |     \
            Read    Write   Mixed
               \     |     /
              Database Layer
                      |
          Benchmark Measurements
                      |
             Analytics Engine
                      |
             Regression Analysis
                      |
             +--------+--------+
             |                 |
         JSON Reports     Run History
                               |
                       Reproducibility
                           Manifests
```

## Installation

### Prerequisites

- Python 3.11 or later
- Git
- PostgreSQL for PostgreSQL-backed benchmarking, or SQLite for local development

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/DBPulse.git
cd DBPulse
```

Replace `YOUR_USERNAME` with your GitHub username.

### 2. Create a virtual environment

**Windows PowerShell**

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If Python 3.11 is not installed, install a supported Python version before continuing.

### 3. Install DBPulse

```powershell
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

### 4. Verify the installation

```powershell
dbpulse --help
dbpulse version
dbpulse config-check
```

## Quick Start

### Check database connectivity

```powershell
dbpulse db-health
```

### Initialize the database schema

```powershell
dbpulse init-db
```

### Seed the dataset

```powershell
dbpulse seed-data
```

### Execute a read benchmark

```powershell
dbpulse benchmark-workload --workload read --iterations 100 --dataset-size 1000 --name read-baseline --profile standard
```

### Execute a write benchmark

```powershell
dbpulse benchmark-workload --workload write --iterations 100 --dataset-size 1000 --name write-baseline --profile standard
```

### Execute a mixed benchmark

```powershell
dbpulse benchmark-workload --workload mixed --iterations 100 --dataset-size 1000 --name mixed-baseline --profile standard
```

Record the run ID printed by each successful benchmark.

> **Note:** The examples above use the CLI options implemented by DBPulse. Confirm the current command defaults and option behavior with `dbpulse benchmark-workload --help`.

## Analyze Benchmark Results

DBPulse calculates descriptive latency statistics for completed benchmark runs.

| Metric | Description |
|---|---|
| Mean | Average measured operation latency |
| Minimum | Lowest observed latency |
| Maximum | Highest observed latency |
| P50 | Median latency |
| P95 | 95th-percentile latency |
| P99 | 99th-percentile latency |

Percentile metrics help reveal tail-latency behavior that averages alone can hide.

### View benchmark history

```powershell
dbpulse history
```

### Inspect a specific run

```powershell
dbpulse show-run RUN_ID
```

Replace `RUN_ID` with an actual run ID.

## Performance Regression Detection

DBPulse compares a baseline run against a candidate run and evaluates changes in mean, P95, and P99 latency.

```powershell
dbpulse compare BASELINE_ID CANDIDATE_ID --threshold 10
```

The threshold specifies the percentage increase tolerated before a metric is flagged as a regression.

For a valid comparison, use runs with matching workload types and consistent configurations.

### Export a JSON comparison report

```powershell
New-Item -ItemType Directory -Force .\reports\generated | Out-Null

dbpulse report BASELINE_ID CANDIDATE_ID --output .\reports\generated\comparison.json
```

The report includes run details, latency statistics, percentage changes, and the overall regression result.

## Reproducibility Manifest

Generate a manifest describing the planned benchmark configuration:

```powershell
dbpulse manifest --profile standard --workload read --iterations 100 --dataset-size 1000 --output .\reports\generated\benchmark-manifest.json
```

The manifest records benchmark parameters and environment details to support repeatable experiments.

Do not publish database passwords, access tokens, or other credentials in manifests or repository files.

## Benchmark Profiles

DBPulse provides three predefined profiles:

| Profile | Intended use |
|---|---|
| `smoke` | Quick functional checks |
| `standard` | General benchmarking |
| `repeatable` | More extensive benchmark runs |

View available profiles:

```powershell
dbpulse profiles
```

Explicit workload parameters and profile behavior should be checked against the installed CLI help.

## Configuration

DBPulse reads its default settings from:

```text
config/dbpulse.toml
```

The configuration controls database connectivity, workload settings, iteration counts, dataset size, warm-up behavior, and regression thresholds where supported by the current implementation.

For PostgreSQL, use a valid connection URL and keep credentials outside source control. Where supported by your configuration, the database URL can be overridden with the `DBPULSE_DATABASE_URL` environment variable.

Example PowerShell pattern:

```powershell
$env:DBPULSE_DATABASE_URL = "YOUR_DATABASE_CONNECTION_URL"
```

Replace the placeholder with your own connection URL. Never commit a real password or secret to GitHub.

## Testing and Code Quality

Run the automated tests:

```powershell
python -m pytest -v
```

Check code quality:

```powershell
ruff check .
ruff format --check .
```

The project has completed a validation run with **58 passing tests**, successful Ruff checks, and 21 formatted Python files.

These results describe the recorded local validation run; rerun the commands after making changes.

## Design Considerations

DBPulse is designed around several performance-engineering principles:

- Compare equivalent workloads rather than unrelated operations.
- Track percentile latency instead of relying exclusively on averages.
- Preserve measurements and run metadata for later investigation.
- Export machine-readable reports for automation.
- Record environment details to improve reproducibility.
- Treat performance comparisons as measurements, not guarantees.

## Current Limitations

- Benchmark results are sensitive to system load, database state, cache behavior, and execution environment.
- Small sample sizes can make tail-latency percentiles unstable.
- A local benchmark does not automatically represent production database behavior.
- A regression threshold is a configurable detection rule, not proof of statistical significance.
- PostgreSQL support does not by itself establish compatibility or performance against every Supabase-specific service or configuration.

## Future Enhancements

Potential extensions include:

- Repeated trials and statistical confidence intervals
- Automated performance-regression gates in CI/CD
- Query-plan capture and query-level profiling
- Concurrency and connection-pool stress testing
- Historical performance trend visualization
- Automated regression triage and diagnostic reports
- Dedicated Supabase environment benchmarking

These are potential future enhancements, not claims about existing functionality.

## Why DBPulse?

DBPulse brings benchmarking, latency analytics, regression detection, historical measurements, and reproducibility metadata into a single developer-oriented workflow.

It demonstrates practical experience with Python tooling, relational databases, performance measurement, automated testing, and structured engineering reports.

## License

Add a `LICENSE` file before distributing the project under an open-source license. Choose a license that matches your intended usage and distribution terms.

## Author

**Yash Kalbhile**

GitHub: [YOUR_GITHUB_PROFILE](https://github.com/YOUR_USERNAME)

