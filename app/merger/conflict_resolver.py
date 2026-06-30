# app/merger/conflict_resolver.py
#
# Module 8: Conflict Resolution
#
# When two sources provide different values for the same field,
# we need to decide which one to keep.
#
# Example:
#   Resume says:   full_name = "John Doe"
#   LinkedIn says: full_name = "Johnathan Doe"
#   GitHub says:   full_name = "John D"
#
# Resolution strategy: Source Priority
# We defined in constants.py that Resume > LinkedIn > GitHub.
# So "John Doe" wins.
#
# Alternative strategy (used for skills): Union (keep all unique values)
# We don't need to "resolve" skills — we keep all of them from all sources.

import json
import os
from typing import Any, Optional, List
from app.utils.constants import PRIORITY_ORDER
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Load the source priority config file
_CONFIG_PATH = os.path.join("app", "config", "source_priority.json")
try:
    with open(_CONFIG_PATH, "r") as f:
        _PRIORITY_CONFIG = json.load(f)
    _SOURCE_PRIORITY = _PRIORITY_CONFIG.get("priority", PRIORITY_ORDER)
except Exception:
    # Fall back to constants if config file is missing
    _SOURCE_PRIORITY = PRIORITY_ORDER


def get_source_priority(source: str) -> int:
    """
    Get the priority number for a source.
    Lower number = higher priority = wins in conflicts.

    Parameters:
        source (str): Source name, e.g. "Resume"

    Returns:
        int: Priority number (1 = highest priority)
             Returns 99 if source is unknown (lowest priority)
    """
    return _SOURCE_PRIORITY.get(source, 99)


def resolve_scalar(values_with_sources: List[tuple]) -> Any:
    """
    Resolve a conflict for a scalar (single-value) field like full_name.

    Given a list of (value, source) pairs, return the value from the
    highest-priority source.

    Parameters:
        values_with_sources (List[tuple]): List of (value, source) pairs
            Example: [
                ("John Doe", "Resume"),
                ("Johnathan Doe", "LinkedIn"),
                ("John D", "GitHub")
            ]

    Returns:
        Any: The value from the highest-priority source

    Example:
        resolve_scalar([
            ("John Doe", "Resume"),       ← priority 1
            ("Johnathan Doe", "LinkedIn") ← priority 3
        ])
        → "John Doe"
    """
    if not values_with_sources:
        return None

    # Filter out None/empty values
    valid = [(val, src) for val, src in values_with_sources if val]

    if not valid:
        return None

    if len(valid) == 1:
        return valid[0][0]   # Only one value, no conflict

    # Sort by priority (ascending = highest priority first)
    # key= is a function that returns the sort key for each item
    # item[1] is the source name, get_source_priority converts it to a number
    sorted_values = sorted(valid, key=lambda item: get_source_priority(item[1]))

    winner_value, winner_source = sorted_values[0]
    if len(valid) > 1:
        # Log the conflict resolution
        all_values = [(v, s) for v, s in sorted_values]
        logger.info(
            f"Conflict resolved: '{winner_value}' ({winner_source}) won over "
            f"{[(v, s) for v, s in all_values[1:]]}"
        )

    return winner_value


def resolve_winner_source(values_with_sources: List[tuple]) -> Optional[str]:
    """
    Like resolve_scalar(), but returns the WINNING SOURCE NAME instead of the value.
    Used for provenance tracking.

    Parameters:
        values_with_sources (List[tuple]): List of (value, source) pairs

    Returns:
        str: Name of the source that won, or None
    """
    valid = [(val, src) for val, src in values_with_sources if val]
    if not valid:
        return None

    sorted_values = sorted(valid, key=lambda item: get_source_priority(item[1]))
    return sorted_values[0][1]


def merge_location(locations_with_sources: List[tuple]) -> dict:
    """
    Merge location data from multiple sources.

    Strategy: Build the most complete location possible.
    For each sub-field (city, region, country), pick the value from
    the highest-priority source that has a non-empty value.

    Parameters:
        locations_with_sources (List[tuple]): List of (location_dict, source) pairs

    Returns:
        dict: Merged location dict {"city": str, "region": str, "country": str}
    """
    city_candidates    = []
    region_candidates  = []
    country_candidates = []

    for loc, source in locations_with_sources:
        if not loc:
            continue
        if loc.get("city"):
            city_candidates.append((loc["city"], source))
        if loc.get("region"):
            region_candidates.append((loc["region"], source))
        if loc.get("country"):
            country_candidates.append((loc["country"], source))

    return {
        "city":    resolve_scalar(city_candidates) or "",
        "region":  resolve_scalar(region_candidates) or "",
        "country": resolve_scalar(country_candidates) or "",
    }
