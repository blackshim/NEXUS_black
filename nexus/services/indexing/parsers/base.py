"""Parser base interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ParsedPage:
    """Result of parsing a single page/sheet."""
    page_or_sheet: int | str  # PDF page number or Excel sheet name
    text: str
    tables: list[str] = field(default_factory=list)  # Tables converted to text
    metadata: dict = field(default_factory=dict)


@dataclass
class ParsedDocument:
    """Entire parsed document."""
    file_path: str
    file_type: str  # pdf, xlsx, docx, pptx, txt, csv, hwp
    pages: list[ParsedPage] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)  # Document-level metadata (title, author, etc.)


class BaseParser(ABC):
    """Base class for all parsers."""

    supported_extensions: list[str] = []

    @abstractmethod
    def parse(self, file_path: Path) -> ParsedDocument:
        """Parse a file and return a ParsedDocument."""
        ...

    def can_parse(self, file_path: Path) -> bool:
        return file_path.suffix.lower() in self.supported_extensions
