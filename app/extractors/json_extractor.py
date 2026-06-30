import json
from app.utils.logger import get_logger
from typing import Dict, Any

logger = get_logger(__name__)


def extract_from_json(file_path: str) -> Dict[str, Any]:
    """Load a JSON file and return it as a Python dict."""
    logger.info(f"Extracting data from JSON: {file_path}")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        logger.info(f"JSON extraction complete. Keys: {list(data.keys()) if isinstance(data, dict) else 'list'}")
        return data if isinstance(data, dict) else {}
    except FileNotFoundError:
        logger.error(f"JSON not found: {file_path}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON: {file_path} | {e}")
        return {}
    except Exception as e:
        logger.error(f"Failed to extract JSON: {file_path} | {e}")
        return {}
