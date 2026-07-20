"""Smoke tests de compatibilidade do núcleo ZeusExAI."""

from __future__ import annotations

import importlib
import sys

import pytest


CORE_MODULES = [
    "openjarvis.zeusex",
    "openjarvis.zeusex.runtime",
    "openjarvis.zeusex.skills",
    "openjarvis.zeusex.voice",
    "openjarvis.zeusex.voice_runtime",
    "openjarvis.zeusex.voice_backends",
    "openjarvis.zeusex.voice_diagnostics",
]


@pytest.mark.parametrize("module_name", CORE_MODULES)
def test_core_modules_import_without_optional_audio_dependencies(module_name: str) -> None:
    module = importlib.import_module(module_name)
    assert module is not None


def test_optional_audio_dependencies_are_not_imported_by_core_imports() -> None:
    for module_name in CORE_MODULES:
        importlib.import_module(module_name)

    assert "sounddevice" not in sys.modules
    assert "faster_whisper" not in sys.modules
    assert "pyttsx3" not in sys.modules


def test_supported_python_range_matches_project_policy() -> None:
    assert (3, 10) <= sys.version_info[:2] < (3, 14)
