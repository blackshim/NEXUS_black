"""nexus.config.yaml loader."""

import os
from pathlib import Path

import yaml

_config: dict | None = None


def load_config(config_path: str | None = None) -> dict:
    """Load and cache the NEXUS configuration file."""
    global _config
    if _config is not None:
        return _config

    if config_path is None:
        config_path = os.environ.get(
            "NEXUS_CONFIG_PATH", "/app/nexus.config.yaml"
        )

    path = Path(config_path)
    if not path.exists():
        # Fallback for local development
        local = Path(__file__).parent.parent.parent.parent / "nexus.config.yaml"
        if local.exists():
            path = local
        else:
            return {}

    with open(path, "r", encoding="utf-8") as f:
        _config = yaml.safe_load(f) or {}

    return _config


def get_indexing_config() -> dict:
    return load_config().get("indexing", {})


def get_search_config() -> dict:
    return load_config().get("search", {})


def get_llm_config() -> dict:
    return load_config().get("llm", {})


def get_rbac_config() -> dict:
    return load_config().get("rbac", {})


def get_ocr_config() -> dict:
    return load_config().get("ocr", {})


def get_embedding_config() -> dict:
    return load_config().get("embedding", {})
