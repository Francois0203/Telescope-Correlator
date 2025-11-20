"""Configuration helpers.

Small helper to load YAML configuration files for runtime settings.
"""
from __future__ import annotations

import yaml
from typing import Any, Dict


def load_yaml(path: str) -> Dict[str, Any]:
    """Load a YAML file and return a dict.
    """
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
