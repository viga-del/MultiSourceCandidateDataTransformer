# app/normalizers/date_normalizer.py
#
# Converts various date formats to the YYYY-MM standard.
# Resumes use many different date formats:
#   "Jan 2023", "January 2023", "01/2023", "2023", "Present", "Current"
# We normalize all of these.

from dateutil import parser as dateutil_parser
# dateutil can parse almost any human-readable date string.
# It's much smarter than Python's built-in datetime.strptime.

import re
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Words that mean "currently working here"
PRESENT_KEYWORDS = {"present", "current", "now", "ongoing", "till date", "till now", "—", "-"}


def normalize_date(raw_date: str) -> str:
    """
    Convert a date string to YYYY-MM format.

    Parameters:
        raw_date (str): Date in any format

    Returns:
        str: Date in "YYYY-MM" format, "Present" for current positions,
             or the original string if parsing fails.

    Examples:
        "Jan 2023"        → "2023-01"
        "January 2023"    → "2023-01"
        "01/2023"         → "2023-01"
        "2023"            → "2023-01"  (assumes January if no month given)
        "Present"         → "Present"
        "Current"         → "Present"
    """
    if not raw_date:
        return ""

    cleaned = raw_date.strip()

    # Check if this means "currently working here"
    # .lower() for case-insensitive comparison
    if cleaned.lower() in PRESENT_KEYWORDS:
        return "Present"

    try:
        # dateutil_parser.parse() is very flexible — it understands:
        # "Jan 2023", "January, 2023", "01-2023", "2023-01", "Jan '23", etc.
        # default= sets the day to 1 when no day is specified (we only want YYYY-MM)
        # fuzzy=True ignores extra text around the date
        from datetime import datetime
        default_date = datetime(2000, 1, 1)   # day=1 is used when not specified
        parsed = dateutil_parser.parse(cleaned, default=default_date, fuzzy=True)

        # strftime formats the datetime object as a string
        # "%Y" = 4-digit year, "%m" = 2-digit month (zero-padded)
        normalized = parsed.strftime("%Y-%m")
        logger.debug(f"Date normalized: '{raw_date}' → '{normalized}'")
        return normalized

    except (ValueError, OverflowError):
        # dateutil couldn't parse it — return original
        logger.warning(f"Could not parse date: '{raw_date}'")
        return cleaned
