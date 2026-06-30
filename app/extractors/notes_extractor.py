from app.utils.logger import get_logger

logger = get_logger(__name__)


def extract_from_notes(file_path: str) -> str:
    """Read a plain text recruiter notes file and return its full contents."""
    logger.info(f"Extracting notes from: {file_path}")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        logger.info(f"Notes extraction complete. Characters: {len(content)}")
        return content
    except FileNotFoundError:
        logger.error(f"Notes file not found: {file_path}")
        return ""
    except Exception as e:
        logger.error(f"Failed to extract notes: {file_path} | {e}")
        return ""
