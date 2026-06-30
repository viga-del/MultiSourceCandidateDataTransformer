# app/normalizers/name_normalizer.py
#
# Normalizes candidate names.
# Different sources may format names differently:
#   "john doe", "JOHN DOE", "Doe, John", "John  Doe" (extra space)
# We convert all of these to "John Doe" (Title Case).

import re
from app.utils.logger import get_logger

logger = get_logger(__name__)


def normalize_name(raw_name: str) -> str:
    """
    Clean and standardize a candidate name.

    Steps:
    1. Strip leading/trailing whitespace
    2. Collapse multiple spaces into one
    3. Handle "Last, First" format → "First Last"
    4. Convert to Title Case

    Parameters:
        raw_name (str): Name in any format

    Returns:
        str: Cleaned name in Title Case

    Examples:
        "john doe"     → "John Doe"
        "JOHN DOE"     → "John Doe"
        "Doe, John"    → "John Doe"
        "john  doe"    → "John Doe"
    """
    if not raw_name:
        return ""

    name = raw_name.strip()

    # Collapse multiple spaces/tabs/newlines into a single space
    name = re.sub(r"\s+", " ", name)

    # Handle "Last, First" format (common in formal documents)
    # If there's a comma, assume it's "Last, First" and reverse it
    if "," in name:
        parts = name.split(",", 1)   # Split on first comma only
        # parts[0] = Last, parts[1] = First (possibly with spaces)
        name = f"{parts[1].strip()} {parts[0].strip()}"

    # Title case: first letter of each word capitalized, rest lowercase
    # "john doe" → "John Doe"
    # Note: .title() handles simple cases well.
    # For names with apostrophes like "O'Brien", .title() gives "O'Brien" correctly.
    name = name.title()

    logger.debug(f"Name normalized: '{raw_name}' → '{name}'")
    return name


def split_full_name(full_name: str) -> tuple:
    """
    Split a full name into first and last name.

    Parameters:
        full_name (str): e.g. "John Michael Doe"

    Returns:
        tuple: (first_name, last_name)
               For "John Michael Doe" → ("John", "Doe")
               For "John" → ("John", "")
    """
    if not full_name:
        return ("", "")

    parts = full_name.strip().split()
    if len(parts) == 1:
        return (parts[0], "")
    elif len(parts) >= 2:
        # First word = first name, last word = last name
        # Middle names are ignored
        return (parts[0], parts[-1])
    return ("", "")
