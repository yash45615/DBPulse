"""Tests for benchmark reproducibility manifests."""

import json

import pytest

from dbpulse.manifest import build_manifest, write_manifest


def test_manifest_contains_reproducibility_details():
    manifest = build_manifest(
        profile_name="standard",
        workload="read",
        database_url="sqlite:///./dbpulse.db",
    )

    assert manifest["manifest_version"] == 1
    assert manifest["profile"]["name"] == "standard"
    assert manifest["workload"]["type"] == "read"
    assert manifest["workload"]["iterations"] == 100
    assert manifest["workload"]["dataset_size"] == 1000
    assert manifest["environment"]["database_backend"] == "sqlite"
    assert manifest["environment"]["python_version"]


def test_manifest_accepts_explicit_overrides():
    manifest = build_manifest(
        profile_name="smoke",
        workload="mixed",
        database_url="sqlite:///./dbpulse.db",
        iterations=30,
        dataset_size=200,
    )

    assert manifest["workload"]["iterations"] == 30
    assert manifest["workload"]["dataset_size"] == 200


def test_manifest_does_not_expose_database_password():
    manifest = build_manifest(
        profile_name="smoke",
        workload="read",
        database_url="postgresql+psycopg://dbuser:secret-password@localhost/db",
    )

    serialized = json.dumps(manifest)

    assert "secret-password" not in serialized
    assert manifest["environment"]["database_backend"] == "postgresql"


@pytest.mark.parametrize(
    ("iterations", "dataset_size"),
    [(0, 100), (10, 0), (-1, 100)],
)
def test_invalid_workload_dimensions_are_rejected(iterations, dataset_size):
    with pytest.raises(ValueError):
        build_manifest(
            profile_name="smoke",
            workload="read",
            database_url="sqlite:///./dbpulse.db",
            iterations=iterations,
            dataset_size=dataset_size,
        )


def test_invalid_workload_is_rejected():
    with pytest.raises(ValueError, match="Unsupported workload"):
        build_manifest(
            profile_name="smoke",
            workload="unknown",
            database_url="sqlite:///./dbpulse.db",
        )


def test_manifest_can_be_written_as_json(tmp_path):
    manifest = build_manifest(
        profile_name="smoke",
        workload="read",
        database_url="sqlite:///./dbpulse.db",
    )
    output = write_manifest(manifest, tmp_path / "nested" / "manifest.json")

    assert output.exists()

    with output.open(encoding="utf-8") as manifest_file:
        loaded = json.load(manifest_file)

    assert loaded["profile"]["name"] == "smoke"
