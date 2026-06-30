# app/merger/duplicate_detector.py
#
# Module 6: Deduplication
# Detects and removes duplicate values before merging.
#
# The same information often appears in multiple sources:
#   Resume → "Java"
#   GitHub → "Java"
#   LinkedIn → "Java"
# We store "Java" only once.
#
# For skills and simple strings, exact match (case-insensitive) is enough.
# For names, we use fuzzy matching because "John Doe" and "Johnathan Doe"
# might be the same person.

from rapidfuzz import fuzz
# rapidfuzz is a fast string similarity library.
# fuzz.ratio() returns a score 0-100 (100 = identical strings).
# fuzz.token_sort_ratio() handles word order variations.

from typing import List, Dict, Any
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Threshold for fuzzy name matching (0-100).
# Names with similarity >= this threshold are considered the same person.
# 85 means: "John Doe" and "Johnathan Doe" (70% similar) → NOT same
#           "John Doe" and "John D." (80% similar) → borderline
#           "John Doe" and "John Doe" (100%) → same
NAME_SIMILARITY_THRESHOLD = 85


def deduplicate_strings(items: List[str]) -> List[str]:
    """
    Remove duplicate strings from a list (case-insensitive comparison).

    Example:
        deduplicate_strings(["Java", "java", "JAVA", "Python"])
        → ["Java", "Python"]

    We keep the FIRST occurrence (which comes from the highest-priority source
    because sources are processed in priority order).

    Parameters:
        items (List[str]): List that may contain duplicates

    Returns:
        List[str]: Deduplicated list preserving first occurrence
    """
    seen = set()
    result = []
    for item in items:
        # Use lowercase as the dedup key so "Java" and "java" are treated as equal
        key = item.lower().strip()
        if key not in seen:
            seen.add(key)
            result.append(item)

    removed = len(items) - len(result)
    if removed > 0:
        logger.debug(f"Deduplicated strings: removed {removed} duplicate(s)")

    return result


def deduplicate_skills(skills: List[str]) -> List[str]:
    """
    Remove duplicate skill names.
    Alias: calls deduplicate_strings since skill names are already normalized.

    Parameters:
        skills (List[str]): Skill names

    Returns:
        List[str]: Unique skill names
    """
    return deduplicate_strings(skills)


def deduplicate_emails(emails: List[str]) -> List[str]:
    """
    Remove duplicate email addresses.
    Emails are already normalized to lowercase, so direct dedup works.

    Parameters:
        emails (List[str]): Email addresses

    Returns:
        List[str]: Unique emails
    """
    return deduplicate_strings(emails)


def deduplicate_phones(phones: List[str]) -> List[str]:
    """
    Remove duplicate phone numbers.
    Phones are already normalized to E.164, so direct dedup works.

    Parameters:
        phones (List[str]): Phone numbers

    Returns:
        List[str]: Unique phone numbers
    """
    return deduplicate_strings(phones)


def deduplicate_experience(experiences: List[Dict]) -> List[Dict]:
    """
    Remove duplicate work experience entries.

    Two experience entries are considered duplicates if they have
    the same company name (case-insensitive, fuzzy match).

    Parameters:
        experiences (List[Dict]): List of experience dicts

    Returns:
        List[Dict]: Deduplicated experience list
    """
    if not experiences:
        return []

    unique = []
    seen_companies = []

    for exp in experiences:
        company = (exp.get("company") or "").lower().strip()
        if not company:
            unique.append(exp)
            continue

        # Check if this company is already in our unique list
        is_duplicate = False
        for seen_company in seen_companies:
            # token_sort_ratio handles "Infosys Ltd" vs "Infosys" gracefully
            similarity = fuzz.token_sort_ratio(company, seen_company)
            if similarity >= NAME_SIMILARITY_THRESHOLD:
                is_duplicate = True
                logger.debug(f"Duplicate experience detected: '{company}' ≈ '{seen_company}' ({similarity}%)")
                break

        if not is_duplicate:
            seen_companies.append(company)
            unique.append(exp)

    return unique


def deduplicate_education(educations: List[Dict]) -> List[Dict]:
    """
    Remove duplicate education entries.

    Two education entries are duplicates if they have the same institution.

    Parameters:
        educations (List[Dict]): List of education dicts

    Returns:
        List[Dict]: Deduplicated education list
    """
    if not educations:
        return []

    unique = []
    seen_institutions = []

    for edu in educations:
        institution = (edu.get("institution") or "").lower().strip()
        if not institution:
            unique.append(edu)
            continue

        is_duplicate = False
        for seen_inst in seen_institutions:
            similarity = fuzz.token_sort_ratio(institution, seen_inst)
            if similarity >= NAME_SIMILARITY_THRESHOLD:
                is_duplicate = True
                break

        if not is_duplicate:
            seen_institutions.append(institution)
            unique.append(edu)

    return unique


def are_same_candidate(name1: str, name2: str) -> bool:
    """
    Check if two name strings likely refer to the same person.

    Uses fuzzy string matching because:
    - "John Doe" and "Johnathan Doe" — LinkedIn might use full name
    - "John D" — GitHub might use abbreviated name

    Parameters:
        name1 (str): First name
        name2 (str): Second name

    Returns:
        bool: True if they're likely the same person
    """
    if not name1 or not name2:
        return False

    n1 = name1.lower().strip()
    n2 = name2.lower().strip()

    if n1 == n2:
        return True

    # token_sort_ratio compares words regardless of order
    # "Doe John" vs "John Doe" still gets a high score
    score = fuzz.token_sort_ratio(n1, n2)
    logger.debug(f"Name similarity: '{name1}' vs '{name2}' = {score}%")
    return score >= NAME_SIMILARITY_THRESHOLD
