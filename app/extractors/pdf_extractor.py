import pdfplumber
from app.utils.logger import get_logger

logger = get_logger(__name__)


def extract_text_from_pdf(file_path: str) -> str:
    """Extract all text from every page of a PDF and return as one string."""
    logger.info(f"Extracting text from PDF: {file_path}")
    try:
        with pdfplumber.open(file_path) as pdf:
            pages_text = []
            for i, page in enumerate(pdf.pages, start=1):
                text = page.extract_text()
                if text:
                    pages_text.append(text)
                else:
                    logger.warning(f"Page {i}: no text found (possibly scanned image)")
            full_text = "\n".join(pages_text)
            logger.info(f"PDF extraction complete. Characters: {len(full_text)}")
            return full_text
    except FileNotFoundError:
        logger.error(f"PDF not found: {file_path}")
        return ""
    except Exception as e:
        logger.error(f"Failed to extract PDF: {file_path} | {e}")
        return ""
