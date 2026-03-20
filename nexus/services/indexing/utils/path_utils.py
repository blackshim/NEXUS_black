"""Path utilities -- workspace mapping, confidential folder detection."""

from pathlib import PurePosixPath, PureWindowsPath
from .config_loader import get_indexing_config


def detect_workspace(file_path: str) -> str:
    """Detect workspace from file path.

    Maps based on workspace_map in nexus.config.yaml.
    Returns "general" if no match found.
    """
    config = get_indexing_config()
    workspace_map = config.get("workspace_map", {})

    # Normalize path to lowercase
    path_lower = file_path.lower().replace("\\", "/")

    for folder_name, workspace in workspace_map.items():
        if folder_name.lower() in path_lower:
            return workspace

    return "general"


def is_confidential(file_path: str) -> bool:
    """Determine if file belongs to a confidential folder."""
    config = get_indexing_config()
    confidential_folders = config.get("confidential_folders", [])

    path_lower = file_path.lower().replace("\\", "/")

    for folder in confidential_folders:
        if folder.lower() in path_lower:
            return True

    return False


def normalize_path(file_path: str) -> str:
    """Normalize Windows/Linux paths."""
    return file_path.replace("\\", "/")
