# app/canonical/canonical_schema.py
#
# Defines the canonical (standard) schema for the candidate profile.
# This module is purely documentation — it shows what fields the canonical
# profile must have and what type each field should be.
# It also provides a factory function to create a blank canonical dict.
#
# "Canonical" means: the one true standard that all sources are converted to.
# No matter if data came from CSV, GitHub, or a PDF resume,
# after canonicalization it all looks like this structure.

from typing import Dict, Any


def create_empty_canonical() -> Dict[str, Any]:
    """
    Create and return an empty canonical candidate dictionary.

    This is the template that all sources get mapped into.
    Every field defaults to None or an empty collection.

    Having this as a function (not a constant) ensures that each call
    gets a brand-new dict with independent empty lists.
    (Same reason we use default_factory in dataclasses.)

    Returns:
        Dict: Empty canonical candidate profile
    """
    return {
        # ── Identity ──────────────────────────────────────────────────
        # All name variants from different sources
        "full_name":  None,   # str: "John Doe"

        # Lists because a candidate can have multiple emails/phones
        "emails":     [],     # List[str]: ["john@gmail.com"]
        "phones":     [],     # List[str]: ["+919876543210"]

        # ── Location ─────────────────────────────────────────────────
        "location": {
            "city":    None,  # str: "Chennai"
            "region":  None,  # str: "Tamil Nadu"
            "country": None,  # str: "IN" (ISO code)
        },

        # ── Links ─────────────────────────────────────────────────────
        "links": {
            "linkedin":  None,   # str: "https://linkedin.com/in/johndoe"
            "github":    None,   # str: "https://github.com/johndoe"
            "portfolio": None,   # str: URL or None
            "other":     [],     # List[str]: other URLs
        },

        # ── Professional ──────────────────────────────────────────────
        "headline":         None,  # str: "Backend Developer"
        "years_experience": None,  # float: 3.5

        # ── Skills ───────────────────────────────────────────────────
        # List of skill name strings (deduplication happens later)
        "skills": [],              # List[str]: ["Java", "Python"]

        # ── Experience ───────────────────────────────────────────────
        # List of experience dicts
        "experience": [],          # List[Dict]

        # ── Education ────────────────────────────────────────────────
        # List of education dicts
        "education": [],           # List[Dict]

        # ── Source tracking (internal, not in final output) ───────────
        # Tracks which source produced this canonical record
        "_source": None,           # str: "Resume", "GitHub", etc.
    }
