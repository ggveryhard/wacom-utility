"""Helpers for locating packaged runtime data."""

import os
from importlib.resources import files
from pathlib import Path


def package_root() -> Path:
    env_dir = os.environ.get("WACOM_UTILITY_DATA_DIR")
    if env_dir:
        return Path(env_dir)
    return Path(str(files("wacom_utility")))


def data_path(*parts: str) -> Path:
    return package_root().joinpath(*parts)
