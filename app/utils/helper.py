import uuid
import hashlib
import re


def generate_candidate_id(full_name: str = "", email: str = "") -> str:
    """Deterministic ID from name+email so the same candidate always gets the same ID."""
    if full_name or email:
        raw = f"{full_name.lower().strip()}{email.lower().strip()}".encode("utf-8")
        return f"C-{hashlib.md5(raw).hexdigest()[:8]}"
    return f"C-{str(uuid.uuid4()).replace('-', '')[:8]}"


def clean_text(text: str) -> str:
    """Collapse multiple whitespace characters into one space and strip edges."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def safe_lower(value: str) -> str:
    """Lowercase safely — returns empty string instead of raising on None."""
    if not value:
        return ""
    return value.lower().strip()


def flatten_list(nested: list) -> list:
    """Flatten one level of nested lists: [["a","b"],"c"] → ["a","b","c"]"""
    result = []
    for item in nested:
        result.extend(item) if isinstance(item, list) else result.append(item)
    return result


def is_valid_url(url: str) -> bool:
    """Return True if string starts with http:// or https://"""
    if not url:
        return False
    return bool(re.match(r"https?://", url.strip()))


def merge_lists_unique(list1: list, list2: list) -> list:
    """Combine two lists keeping only unique values (case-insensitive for strings)."""
    seen = set()
    result = []
    for item in list1 + list2:
        key = item.lower() if isinstance(item, str) else str(item)
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result
