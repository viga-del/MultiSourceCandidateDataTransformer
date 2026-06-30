# app/projection/projection_engine.py
#
# Module 11: Configurable Projection
#
# The projection engine controls WHAT appears in the final JSON output.
# Instead of always outputting every field, we read a config file (projection.json)
# that lists which fields to include.
#
# This means:
# - No code changes needed to change the output format
# - Different deployments can use different projections
# - Example use case: "I only want name, email, and skills in the output"
#   → Just change projection.json, restart the app.

import json
import os
import dataclasses
from typing import Dict, Any, List, Optional
from app.models.candidate  import CandidateProfile
from app.models.skill      import Skill
from app.models.experience import Experience
from app.models.education  import Education
from app.models.provenance import ProvenanceRecord
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Default set of fields to include if no config file is found
DEFAULT_FIELDS = [
    "candidate_id", "full_name", "emails", "phones",
    "location", "links", "headline", "years_experience",
    "skills", "experience", "education", "provenance", "overall_confidence"
]

# Load projection config
_CONFIG_PATH = os.path.join("app", "config", "projection.json")
try:
    with open(_CONFIG_PATH, "r") as f:
        _PROJ_CONFIG = json.load(f)
    FIELDS_TO_PROJECT = _PROJ_CONFIG.get("fields", DEFAULT_FIELDS)
except Exception:
    FIELDS_TO_PROJECT = DEFAULT_FIELDS
    logger.warning("Could not load projection.json — using default fields")


def project_profile(profile: CandidateProfile, fields: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Convert a CandidateProfile into the final output dictionary,
    including only the fields specified in the projection config.

    Parameters:
        profile (CandidateProfile): The fully processed candidate profile
        fields  (List[str]):        Optional override — if provided, use these fields
                                    instead of the config file fields

    Returns:
        Dict: The final output JSON-ready dictionary

    Example:
        If projection.json has fields: ["candidate_id", "full_name", "skills"]
        Then the output will ONLY contain those three fields.
    """
    selected_fields = fields or FIELDS_TO_PROJECT

    # First, serialize the entire profile to a dict
    full_dict = _serialize_profile(profile)

    # Then filter to only include the projected fields
    projected = {}
    for field in selected_fields:
        if field in full_dict:
            projected[field] = full_dict[field]

    logger.info(f"Projection complete — {len(projected)} fields in output")
    return projected


def _serialize_profile(profile: CandidateProfile) -> Dict[str, Any]:
    """
    Convert a CandidateProfile dataclass into a plain JSON-serializable dict.

    Dataclass objects are not directly JSON-serializable — we need to convert
    nested objects (Skill, Experience, Education, ProvenanceRecord) to dicts.

    Parameters:
        profile (CandidateProfile): The profile to serialize

    Returns:
        Dict: Plain Python dict (no custom objects, only str/int/float/list/dict)
    """
    return {
        # ── Identity ─────────────────────────────────────────────────
        "candidate_id":      profile.candidate_id,
        "full_name":         profile.full_name,
        "emails":            profile.emails,
        "phones":            profile.phones,

        # ── Location ─────────────────────────────────────────────────
        # profile.location is already a plain dict
        "location": {
            "city":    profile.location.get("city") or None,
            "region":  profile.location.get("region") or None,
            "country": profile.location.get("country") or None,
        },

        # ── Links ─────────────────────────────────────────────────────
        "links": {
            "linkedin":  profile.links.get("linkedin"),
            "github":    profile.links.get("github"),
            "portfolio": profile.links.get("portfolio"),
            "other":     profile.links.get("other", []),
        },

        # ── Professional ─────────────────────────────────────────────
        "headline":         profile.headline,
        "years_experience": profile.years_experience,

        # ── Skills (list of Skill objects → list of dicts) ────────────
        # Each Skill is: Skill(name="Java", confidence=0.99, sources=["Resume"])
        # We convert to: {"name": "Java", "confidence": 0.99, "sources": ["Resume"]}
        "skills": [
            {
                "name":       skill.name,
                "confidence": skill.confidence,
                "sources":    skill.sources,
            }
            for skill in profile.skills
        ],

        # ── Experience (list of Experience objects → list of dicts) ───
        "experience": [
            {
                "company": exp.company,
                "title":   exp.title,
                "start":   exp.start,
                "end":     exp.end,
                "summary": exp.summary,
            }
            for exp in profile.experience
        ],

        # ── Education (list of Education objects → list of dicts) ─────
        "education": [
            {
                "institution": edu.institution,
                "degree":      edu.degree,
                "field":       edu.field,
                "start_year":  edu.start_year,
                "end_year":    edu.end_year,
            }
            for edu in profile.education
        ],

        # ── Provenance (list of ProvenanceRecord objects → list of dicts)
        "provenance": [
            {
                "field":  rec.field,
                "value":  rec.value,
                "source": rec.source,
                "method": rec.method,
            }
            for rec in profile.provenance
        ],

        # ── Confidence ────────────────────────────────────────────────
        # The per-field confidence dict from the confidence calculator
        "confidence":        profile.confidence,
        "overall_confidence": profile.overall_confidence,
    }
