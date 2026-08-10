"""Pytest collection config: keep the scratch package (taped/scrap) out of collection.

Uses the pytest>=7 ``collection_path``/``config`` hook signature — the legacy
one-argument ``pytest_ignore_collect(path)`` form was removed in pytest 9 and
made every CI run fail with a PluginValidationError before any test ran.
"""

import pathlib


def pytest_ignore_collect(collection_path: pathlib.Path, config) -> bool:
    root_dir = pathlib.Path(__file__).parent.resolve()
    scrap_dir = root_dir / "taped" / "scrap"
    return scrap_dir == collection_path or scrap_dir in collection_path.parents
