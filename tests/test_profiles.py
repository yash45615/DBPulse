"""Tests for named benchmark profiles."""

import pytest

from dbpulse.profiles import get_profile, list_profiles


def test_smoke_profile_is_lightweight():
    profile = get_profile("smoke")

    assert profile.iterations == 20
    assert profile.dataset_size == 100


def test_standard_profile_parameters():
    profile = get_profile("standard")

    assert profile.iterations == 100
    assert profile.dataset_size == 1000


def test_profile_names_are_case_insensitive():
    assert get_profile("STANDARD") == get_profile("standard")


def test_unknown_profile_is_rejected():
    with pytest.raises(ValueError, match="Available profiles"):
        get_profile("unknown")


def test_list_profiles_returns_all_profiles():
    profiles = list_profiles()

    assert {profile["name"] for profile in profiles} == {
        "smoke",
        "standard",
        "repeatable",
    }
