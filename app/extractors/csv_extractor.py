import pandas as pd
from app.utils.logger import get_logger
from typing import List, Dict, Any

logger = get_logger(__name__)


def extract_from_csv(file_path: str) -> List[Dict[str, Any]]:
    """Read a CSV and return each row as a dict. dtype=str prevents phone numbers losing leading zeros."""
    logger.info(f"Extracting data from CSV: {file_path}")
    try:
        df = pd.read_csv(file_path, dtype=str, na_filter=False)
        df.columns = df.columns.str.strip()
        df = df.map(lambda x: x.strip() if isinstance(x, str) else x)
        records = df.to_dict("records")
        logger.info(f"CSV extraction complete. Rows: {len(records)}")
        return records
    except FileNotFoundError:
        logger.error(f"CSV not found: {file_path}")
        return []
    except Exception as e:
        logger.error(f"Failed to extract CSV: {file_path} | {e}")
        return []
