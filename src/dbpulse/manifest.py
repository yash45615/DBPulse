"""Create reproducibility manifests for DBPulse benchmark runs."""

import json
import platform
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.engine import make_url

from dbpulse.profiles import get_profile

SUPPORTED_WORKLOADS = {"read", "write", "mixed"}


def build_manifest(
    profile_name: str,
    workload: str,
    database_url: str,
    iterations: int | None = None,
    dataset_size: int | None = None,
) -> dict[str, Any]:
    """Build a JSON-serializable manifest for a benchmark configuration."""
    profile = get_profile(profile_name)

    if workload not in SUPPORTED_WORKLOADS:
        raise ValueError(
            f"Unsupported workload {workload!r}. "
            f"Choose from: {', '.join(sorted(SUPPORTED_WORKLOADS))}"
        )

    actual_iterations = profile.iterations if iterations is None else iterations
    actual_dataset_size = profile.dataset_size if dataset_size is None else dataset_size

    if actual_iterations < 1:
        raise ValueError("Iterations must be at least 1")

    if actual_dataset_size < 1:
        raise ValueError("Dataset size must be at least 1")

    try:
        parsed_url = make_url(database_url)
    except (ValueError, TypeError) as exc:
        raise ValueError("Invalid database URL") from exc

    return {
        "manifest_version": 1,
        "created_at": datetime.now(UTC).isoformat(),
        "profile": {
            "name": profile.name,
            "description": profile.description,
        },
        "workload": {
            "type": workload,
            "iterations": actual_iterations,
            "dataset_size": actual_dataset_size,
        },
        "environment": {
            "python_version": sys.version.split()[0],
            "python_implementation": platform.python_implementation(),
            "operating_system": platform.platform(),
            "database_backend": parsed_url.get_backend_name(),
            "database_driver": parsed_url.drivername,
        },
    }


def write_manifest(
    manifest: dict[str, Any],
    output_path: str | Path,
) -> Path:
    """Write a manifest as formatted JSON."""
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)

    with destination.open("w", encoding="utf-8") as manifest_file:
        json.dump(manifest, manifest_file, indent=2, allow_nan=False)
        manifest_file.write("\n")

    return destination
