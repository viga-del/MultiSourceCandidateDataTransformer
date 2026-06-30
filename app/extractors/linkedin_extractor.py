import json
from app.utils.logger import get_logger
from typing import Dict, Any

logger = get_logger(__name__)


def extract_from_linkedin_json(file_path: str) -> Dict[str, Any]:
    """Load a LinkedIn JSON export file and return it as a dict."""
    logger.info(f"Extracting LinkedIn JSON: {file_path}")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except FileNotFoundError:
        logger.error(f"LinkedIn file not found: {file_path}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in LinkedIn file: {file_path} | {e}")
        return {}
    except Exception as e:
        logger.error(f"Failed LinkedIn extraction: {file_path} | {e}")
        return {}


def extract_from_linkedin_text(text: str) -> Dict[str, Any]:
    """Wrap a pasted LinkedIn plain text profile so the parser can handle it uniformly."""
    return {"raw_text": text}
