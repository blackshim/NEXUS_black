"""Docling-based PDF/DOCX/PPTX parser + PaddleOCR scanned page processing."""

import logging
from pathlib import Path

from .base import BaseParser, ParsedDocument, ParsedPage

logger = logging.getLogger("nexus.parser.docling")

# === Page classification constants ===
PAGE_TEXT = "text"
PAGE_SCANNED = "scanned"
PAGE_MIXED = "mixed"

GLYPHLESS_FONT_NAME = "GlyphLessFont"  # Previous OCR layer font


def classify_page(
    page,
    *,
    image_coverage_threshold: float = 0.9,
    mixed_coverage_threshold: float = 0.3,
    drawings_threshold: int = 5,
) -> str:
    """Classify a PyMuPDF page as text / scanned / mixed.

    Multi-signal combination:
    1. Image coverage >= threshold -> scanned (highest confidence)
    2. GlyphLessFont detected -> previous OCR text layer (needs re-OCR)
    3. 0 text blocks + image blocks present -> scanned
    4. Vector drawings >= threshold + no text -> scanned (vector-rendered PDF)
    """
    page_rect = page.rect
    page_area = page_rect.width * page_rect.height
    if page_area == 0:
        return PAGE_TEXT

    # --- Signal 1: Image coverage ---
    image_area = 0.0
    for img in page.get_images(full=True):
        try:
            xref = img[0]
            rects = page.get_image_rects(xref)
            for r in rects:
                image_area += r.width * r.height
        except Exception:
            pass
    image_coverage = image_area / page_area

    # --- Signal 2: GlyphLessFont (previous OCR layer) ---
    has_glyphless = False
    fonts = page.get_fonts()
    for font in fonts:
        font_name = font[3] if len(font) > 3 else ""
        if GLYPHLESS_FONT_NAME.lower() in font_name.lower():
            has_glyphless = True
            break

    # --- Signal 3: Text/image block count ---
    # flags: TEXT_PRESERVE_IMAGES(4) included -- required for image block detection
    blocks = page.get_text("dict", flags=4)["blocks"]
    text_blocks = [b for b in blocks if b.get("type") == 0]
    image_blocks = [b for b in blocks if b.get("type") == 1]
    has_text_content = any(
        span.get("text", "").strip()
        for b in text_blocks
        for line in b.get("lines", [])
        for span in line.get("spans", [])
    )

    # --- Signal 4: Vector drawings (text rendered as paths/shapes) ---
    has_drawings = False
    try:
        drawings = page.get_drawings()
        has_drawings = len(drawings) > drawings_threshold
    except Exception:
        pass

    # --- Decision ---
    if image_coverage >= image_coverage_threshold:
        return PAGE_SCANNED
    if has_glyphless:
        return PAGE_SCANNED  # Previous OCR layer -> needs re-OCR
    if not has_text_content and image_blocks:
        return PAGE_SCANNED
    if not has_text_content and has_drawings:
        return PAGE_SCANNED  # Text rendered via vector paths -> needs OCR
    if has_text_content and image_blocks and image_coverage > mixed_coverage_threshold:
        return PAGE_MIXED
    return PAGE_TEXT


class DoclingParser(BaseParser):
    """Universal document parser using Docling.

    Supports PDF, DOCX, PPTX, HTML, images (OCR), etc.
    Falls back to PyMuPDF + PaddleOCR if Docling is unavailable.
    Scanned PDF: classifies pages first, then runs PaddleOCR only on scanned/mixed pages.
    """

    supported_extensions = [".pdf", ".docx", ".pptx", ".html", ".htm"]

    def __init__(self):
        self._docling_available = False
        self._pymupdf_available = False
        self._paddleocr_available = False
        self._ocr_engine = None

        # === Config load ===
        try:
            from utils.config_loader import get_ocr_config
            ocr_config = get_ocr_config()
        except Exception:
            ocr_config = {}

        page_cls = ocr_config.get("page_classification", {})
        self._image_coverage_threshold = page_cls.get("image_coverage_threshold", 0.9)
        self._mixed_coverage_threshold = page_cls.get("mixed_coverage_threshold", 0.3)
        self._drawings_threshold = page_cls.get("drawings_threshold", 5)
        self._scan_sample_pages = page_cls.get("scan_sample_pages", 5)
        self._ocr_dpi = ocr_config.get("dpi", 300)
        self._ocr_lang = ocr_config.get("lang", ["korean", "en"])

        # Initialize Docling (attempt PaddleOCR backend configuration)
        try:
            from docling.document_converter import DocumentConverter, FormatOption
            from docling.datamodel.base_models import InputFormat
            try:
                from docling.datamodel.pipeline_options import PdfPipelineOptions

                ocr_options = None
                try:
                    from docling.datamodel.pipeline_options import PaddleOcrOptions
                    ocr_options = PaddleOcrOptions(lang=self._ocr_lang)
                    logger.info("Docling PaddleOCR backend configured")
                except ImportError:
                    logger.info("Docling PaddleOCR options not available, using Docling defaults")

                pipeline_options = PdfPipelineOptions()
                pipeline_options.do_ocr = True
                if ocr_options:
                    pipeline_options.ocr_options = ocr_options

                self._converter = DocumentConverter(
                    format_options={
                        InputFormat.PDF: FormatOption(pipeline_options=pipeline_options),
                    }
                )
            except (ImportError, Exception) as e:
                logger.info(f"Docling advanced config not available ({e}), using defaults")
                self._converter = DocumentConverter()

            self._docling_available = True
            logger.info("Docling parser initialized")
        except ImportError:
            logger.warning("Docling not available")

        # Check PyMuPDF availability (independent from Docling -- for scanned PDF fallback + classify_page)
        try:
            import fitz  # PyMuPDF
            self._pymupdf_available = True
            logger.info("PyMuPDF available")
        except ImportError:
            if not self._docling_available:
                logger.error("Neither Docling nor PyMuPDF available")

        # Initialize PaddleOCR (for OCR of scanned/vector pages)
        # Use first language from lang list as PaddleOCR default language
        paddleocr_lang = self._ocr_lang[0] if self._ocr_lang else "korean"
        try:
            from paddleocr import PaddleOCR
            self._ocr_engine = PaddleOCR(use_angle_cls=True, lang=paddleocr_lang, show_log=False)
            self._paddleocr_available = True
            logger.info(f"PaddleOCR initialized ({paddleocr_lang})")
        except ImportError:
            logger.info("PaddleOCR not available — scanned pages will have no OCR")

    def parse(self, file_path: Path) -> ParsedDocument:
        suffix = file_path.suffix.lower()
        if suffix != ".pdf":
            # DOCX, PPTX, etc. are Docling-only
            if self._docling_available:
                return self._parse_docling(file_path)
            raise RuntimeError(f"Docling not available for {suffix}")

        # PDF: classify pages first -> use PyMuPDF+PaddleOCR if scanned/mixed pages exist
        has_scanned = self._has_scanned_pages(file_path)
        if has_scanned:
            # Scanned/mixed pages exist -> PyMuPDF + PaddleOCR path
            return self._parse_pymupdf(file_path)
        if self._docling_available:
            return self._parse_docling(file_path)
        if self._pymupdf_available:
            return self._parse_pymupdf(file_path)
        raise RuntimeError("No PDF parser available. Install docling or pymupdf.")

    def _has_scanned_pages(self, file_path: Path) -> bool:
        """Quickly check if PDF has scanned/mixed pages."""
        try:
            import fitz
        except ImportError:
            return False
        try:
            doc = fitz.open(str(file_path))
            total = len(doc)
            sample = self._scan_sample_pages

            # Sample first and last sample pages
            pages_to_check = list(range(min(sample, total)))
            if total > sample * 2:
                pages_to_check += list(range(total - sample, total))
            elif total > sample:
                pages_to_check += list(range(sample, total))

            for i in pages_to_check:
                page = doc[i]
                page_type = classify_page(
                    page,
                    image_coverage_threshold=self._image_coverage_threshold,
                    mixed_coverage_threshold=self._mixed_coverage_threshold,
                    drawings_threshold=self._drawings_threshold,
                )
                if page_type in (PAGE_SCANNED, PAGE_MIXED):
                    doc.close()
                    logger.info(f"Scanned page detected in {file_path.name} (p{i+1}={page_type}), using PyMuPDF+PaddleOCR")
                    return True
            doc.close()
            return False
        except Exception as e:
            logger.warning(f"Page classification check failed: {e}")
            return False

    def _parse_docling(self, file_path: Path) -> ParsedDocument:
        from docling.document_converter import DocumentConverter

        result = self._converter.convert(str(file_path))
        doc = result.document

        pages = []
        # Split Docling text by page
        full_text = doc.export_to_markdown()

        # Difficult to separate by page, so treat the entire content as one page
        tables = []
        if hasattr(doc, 'tables'):
            for table in doc.tables:
                try:
                    tables.append(table.export_to_markdown())
                except Exception:
                    pass

        pages.append(ParsedPage(
            page_or_sheet=1,
            text=full_text,
            tables=tables,
            metadata={}
        ))

        doc_metadata = {}
        if hasattr(result, 'metadata') and result.metadata:
            doc_metadata = dict(result.metadata) if not isinstance(result.metadata, dict) else result.metadata

        return ParsedDocument(
            file_path=str(file_path),
            file_type=file_path.suffix.lower().lstrip('.'),
            pages=pages,
            metadata=doc_metadata
        )

    def _ocr_page_image(self, page) -> str:
        """Render scanned/mixed page as image and extract text using PaddleOCR."""
        if not self._paddleocr_available or self._ocr_engine is None:
            return ""

        import tempfile
        import os

        try:
            # Render page as image (config DPI)
            pix = page.get_pixmap(dpi=self._ocr_dpi)
            tmp_path = tempfile.mktemp(suffix=".png")
            pix.save(tmp_path)

            # Run PaddleOCR
            result = self._ocr_engine.ocr(tmp_path, cls=True)
            os.unlink(tmp_path)

            if not result or not result[0]:
                return ""

            # Combine OCR results as text (top->bottom, left->right order)
            lines = []
            for line_result in result[0]:
                if line_result and len(line_result) >= 2:
                    text = line_result[1][0]  # (text, confidence)
                    lines.append(text)

            return "\n".join(lines)
        except Exception as e:
            logger.warning(f"PaddleOCR failed for page: {e}")
            return ""

    def _parse_pymupdf(self, file_path: Path) -> ParsedDocument:
        """PyMuPDF parsing + per-page classification + PaddleOCR (scanned/mixed)."""
        import fitz

        doc = fitz.open(str(file_path))
        pages = []
        classification_summary = {"text": 0, "scanned": 0, "mixed": 0}

        for page_num in range(len(doc)):
            page = doc[page_num]

            # --- Page classification ---
            page_type = classify_page(
                page,
                image_coverage_threshold=self._image_coverage_threshold,
                mixed_coverage_threshold=self._mixed_coverage_threshold,
                drawings_threshold=self._drawings_threshold,
            )
            classification_summary[page_type] += 1

            # --- Text extraction (classification-based) ---
            if page_type == PAGE_TEXT:
                text = page.get_text("text")
            elif page_type == PAGE_SCANNED:
                # scanned -> use PaddleOCR only
                text = self._ocr_page_image(page)
            else:
                # mixed -> PyMuPDF text + PaddleOCR supplement
                pymupdf_text = page.get_text("text")
                ocr_text = self._ocr_page_image(page)
                # Merge if already extracted text exists, minimizing duplicates
                if ocr_text and len(ocr_text) > len(pymupdf_text):
                    text = ocr_text
                else:
                    text = pymupdf_text

            # --- Table extraction attempt ---
            tables = []
            try:
                page_tables = page.find_tables()
                for table in page_tables.tables if hasattr(page_tables, 'tables') else page_tables:
                    try:
                        df = table.to_pandas()
                        tables.append(df.to_markdown(index=False))
                    except Exception:
                        try:
                            cells = table.extract()
                            if cells and len(cells) > 0:
                                header = [str(c) if c else "" for c in cells[0]]
                                md = " | ".join(header) + "\n"
                                md += " | ".join(["---"] * len(header)) + "\n"
                                for row in cells[1:]:
                                    md += " | ".join(str(c) if c else "" for c in row) + "\n"
                                tables.append(md)
                        except Exception:
                            pass
            except Exception:
                pass

            if text.strip() or tables:
                pages.append(ParsedPage(
                    page_or_sheet=page_num + 1,
                    text=text,
                    tables=tables,
                    metadata={"page_type": page_type}
                ))

        doc_metadata = {}
        meta = doc.metadata
        if meta:
            if meta.get("title"):
                doc_metadata["title"] = meta["title"]
            if meta.get("author"):
                doc_metadata["author"] = meta["author"]

        doc_metadata["page_classification"] = classification_summary
        total = sum(classification_summary.values())
        if classification_summary["scanned"] + classification_summary["mixed"] > 0:
            logger.info(
                f"PDF classification: {file_path.name} — "
                f"text={classification_summary['text']}, "
                f"scanned={classification_summary['scanned']}, "
                f"mixed={classification_summary['mixed']} "
                f"(total {total} pages)"
            )

        doc.close()

        return ParsedDocument(
            file_path=str(file_path),
            file_type="pdf",
            pages=pages,
            metadata=doc_metadata
        )
