"""Text file parser. TXT, MD, LOG, etc."""

import logging
from pathlib import Path

from .base import BaseParser, ParsedDocument, ParsedPage

logger = logging.getLogger("nexus.parser.text")


def _load_file_encodings() -> list[str]:
    """Load file encoding fallback list."""
    try:
        from utils.config_loader import get_indexing_config
        return get_indexing_config().get("file_encodings", ["utf-8", "cp949", "euc-kr", "latin-1"])
    except Exception:
        return ["utf-8", "cp949", "euc-kr", "latin-1"]


class TextParser(BaseParser):
    """General text file parser."""

    supported_extensions = [".txt", ".md", ".log", ".json", ".xml", ".yaml", ".yml"]

    def parse(self, file_path: Path) -> ParsedDocument:
        text = ""
        for encoding in _load_file_encodings():
            try:
                text = file_path.read_text(encoding=encoding)
                break
            except (UnicodeDecodeError, UnicodeError):
                continue

        pages = [ParsedPage(page_or_sheet=1, text=text)]

        return ParsedDocument(
            file_path=str(file_path),
            file_type=file_path.suffix.lower().lstrip('.'),
            pages=pages,
        )
