"""Parser factory -- returns the appropriate parser based on file extension."""

from pathlib import Path

from .base import BaseParser
from .pdf_parser import DoclingParser
from .excel_parser import ExcelParser
from .text_parser import TextParser

_parsers: list[BaseParser] | None = None


def _init_parsers() -> list[BaseParser]:
    return [
        DoclingParser(),
        ExcelParser(),
        TextParser(),
    ]


def get_parser(file_path: str | Path) -> BaseParser | None:
    """Return a parser matching the file path. Returns None if none found."""
    global _parsers
    if _parsers is None:
        _parsers = _init_parsers()

    path = Path(file_path)
    for parser in _parsers:
        if parser.can_parse(path):
            return parser
    return None
