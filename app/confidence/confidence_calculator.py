# app/confidence/confidence_calculator.py
#
# Module 9: Confidence Calculation
#
# Every piece of data gets a confidence score (0.0 to 1.0).
# This tells the recruiter how trustworthy each field is.
#
# Scoring logic:
# 1. Base confidence comes from the source (Resume=0.95, GitHub=0.75, etc.)
# 2. If multiple sources agree, confidence is boosted
# 3. Capped at MAX_CONFIDENCE (0.99) — we never say 100% certain
# 4. Overall confidence is a weighted average of key field scores

import json
import os
from typing import List, Dict
from app.models.candidate import CandidateProfile
from app.utils.constants import (
    CONFIDENCE_RESUME, CONFIDENCE_CSV, CONFIDENCE_JSON,
    CONFIDENCE_LINKEDIN, CONFIDENCE_GITHUB, CONFIDENCE_NOTES,
    SOURCE_RESUME, SOURCE_CSV, SOURCE_JSON,
    SOURCE_LINKEDIN, SOURCE_GITHUB, SOURCE_NOTES,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Load confidence rules from config file
_CONFIG_PATH = os.path.join("app", "config", "confidence_rules.json")
try:
    with open(_CONFIG_PATH, "r") as f:
        _CONF_CONFIG = json.load(f)
    BASE_CONFIDENCE = _CONF_CONFIG.get("base_confidence", {
        SOURCE_RESUME:   CONFIDENCE_RESUME,
        SOURCE_CSV:      CONFIDENCE_CSV,
        SOURCE_JSON:     CONFIDENCE_JSON,
        SOURCE_LINKEDIN: CONFIDENCE_LINKEDIN,
        SOURCE_GITHUB:   CONFIDENCE_GITHUB,
        SOURCE_NOTES:    CONFIDENCE_NOTES,
    })
    MULTI_SOURCE_BOOST = _CONF_CONFIG.get("multi_source_boost", 0.05)
    MAX_CONFIDENCE     = _CONF_CONFIG.get("max_confidence", 0.99)
    FIELD_WEIGHTS      = _CONF_CONFIG.get("field_weights", {
        "full_name": 0.20,
        "emails":    0.20,
        "phones":    0.15,
        "skills":    0.25,
        "experience":0.20,
    })
except Exception:
    BASE_CONFIDENCE = {
        SOURCE_RESUME: 0.95, SOURCE_CSV: 0.90, SOURCE_JSON: 0.90,
        SOURCE_LINKEDIN: 0.85, SOURCE_GITHUB: 0.75, SOURCE_NOTES: 0.70,
    }
    MULTI_SOURCE_BOOST = 0.05
    MAX_CONFIDENCE     = 0.99
    FIELD_WEIGHTS      = {"full_name":0.20, "emails":0.20, "phones":0.15, "skills":0.25, "experience":0.20}


def calculate_source_confidence(sources: List[str]) -> float:
    """
    Calculate confidence for a value based on which sources provided it.

    Algorithm:
    1. Start with the highest base confidence among the contributing sources
    2. For each ADDITIONAL source that confirms the value, add MULTI_SOURCE_BOOST
    3. Cap at MAX_CONFIDENCE

    Example:
        Java found in: Resume (0.95), GitHub (0.75), LinkedIn (0.85)
        → Start: 0.95 (highest base)
        → +0.05 for GitHub confirmation  → 1.00, capped to 0.99
        → +0.05 for LinkedIn confirmation → 1.04, capped to 0.99
        → Result: 0.99

    Example:
        Python found in: GitHub (0.75) only
        → Start: 0.75
        → No additional sources
        → Result: 0.75

    Parameters:
        sources (List[str]): Source names that provided this value

    Returns:
        float: Confidence score between 0.0 and MAX_CONFIDENCE
    """
    if not sources:
        return 0.0

    # Get base confidence for each source
    base_scores = [BASE_CONFIDENCE.get(source, 0.60) for source in sources]

    # Start with the highest base score
    confidence = max(base_scores)

    # Add boost for each additional confirming source
    # (subtract 1 because the first source is already counted)
    additional_sources = len(sources) - 1
    confidence += additional_sources * MULTI_SOURCE_BOOST

    # Cap at maximum
    confidence = min(confidence, MAX_CONFIDENCE)

    # Round to 2 decimal places for clean output
    return round(confidence, 2)


def calculate_field_confidence(value: any, sources: List[str]) -> float:
    """
    Calculate confidence for a single field value.
    Same as calculate_source_confidence — just a clearer name for field-level usage.

    Parameters:
        value   : The field value (used to check if it exists)
        sources : Sources that provided this value

    Returns:
        float: Confidence score
    """
    if not value:
        return 0.0
    return calculate_source_confidence(sources)


def calculate_all_confidences(profile: CandidateProfile) -> CandidateProfile:
    """
    Calculate and assign confidence scores for all fields in the profile.

    This function:
    1. Assigns confidence to each Skill object
    2. Calculates per-field confidence (name, emails, phones, etc.)
    3. Calculates the overall_confidence as a weighted average

    Parameters:
        profile (CandidateProfile): The merged candidate profile

    Returns:
        CandidateProfile: Same profile with confidence scores filled in
    """
    logger.info("Calculating confidence scores...")

    sources = profile._sources_processed   # e.g. ["Resume", "GitHub"]

    # ── Skills confidence ─────────────────────────────────────────────
    # Each Skill object already has a .sources list from the merge engine
    for skill in profile.skills:
        skill.confidence = calculate_source_confidence(skill.sources)

    # ── Per-field confidence ──────────────────────────────────────────

    # full_name: confidence based on which sources provided a name
    name_sources = [s for s in sources if s]  # We know all sources tried to give a name
    profile.confidence["full_name"] = calculate_field_confidence(
        profile.full_name, name_sources
    )

    # emails: if we have emails, they came from sources — use all sources
    if profile.emails:
        profile.confidence["emails"] = calculate_field_confidence(
            profile.emails, sources
        )
    else:
        profile.confidence["emails"] = 0.0

    # phones: same logic
    if profile.phones:
        profile.confidence["phones"] = calculate_field_confidence(
            profile.phones, sources
        )
    else:
        profile.confidence["phones"] = 0.0

    # skills: average confidence of all skills
    if profile.skills:
        avg_skill_conf = sum(s.confidence for s in profile.skills) / len(profile.skills)
        profile.confidence["skills"] = round(avg_skill_conf, 2)
    else:
        profile.confidence["skills"] = 0.0

    # experience: if we have experience data, assign confidence
    if profile.experience:
        profile.confidence["experience"] = calculate_field_confidence(
            profile.experience, sources
        )
    else:
        profile.confidence["experience"] = 0.0

    # ── Overall confidence (weighted average) ─────────────────────────
    # overall = sum(field_weight * field_confidence) for all weighted fields
    total_weight = 0.0
    weighted_sum = 0.0

    for field, weight in FIELD_WEIGHTS.items():
        field_conf = profile.confidence.get(field, 0.0)
        if field_conf > 0:
            weighted_sum += weight * field_conf
            total_weight  += weight

    if total_weight > 0:
        overall = weighted_sum / total_weight
        profile.overall_confidence = round(min(overall, MAX_CONFIDENCE), 2)
    else:
        profile.overall_confidence = 0.0

    logger.info(
        f"Confidence calculated — "
        f"overall: {profile.overall_confidence}, "
        f"skills avg: {profile.confidence.get('skills', 0.0)}"
    )

    return profile
