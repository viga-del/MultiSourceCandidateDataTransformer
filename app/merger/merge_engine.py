# app/merger/merge_engine.py
#
# Module 7: Merge Engine
#
# Takes canonical data from ALL sources and combines them into
# one unified CandidateProfile object.
#
# For each field, the merge strategy is:
#   Scalar fields (name, headline): Conflict resolution → highest priority source wins
#   List fields (emails, phones):   Union → combine all unique values from all sources
#   Skills:                         Union → merge all unique skills from all sources
#                                   + track which sources mentioned each skill
#   Experience:                     Union → combine entries, dedup by company
#   Education:                      Union → combine entries, dedup by institution

from typing import List, Dict, Any
from app.models.candidate  import CandidateProfile
from app.models.skill      import Skill
from app.models.experience import Experience
from app.models.education  import Education
from app.merger.duplicate_detector import (
    deduplicate_strings,
    deduplicate_skills,
    deduplicate_emails,
    deduplicate_phones,
    deduplicate_experience,
    deduplicate_education,
)
from app.merger.conflict_resolver import (
    resolve_scalar,
    resolve_winner_source,
    merge_location,
)
from app.utils.logger import get_logger
from app.utils.helper import generate_candidate_id

logger = get_logger(__name__)


def merge_canonical_sources(canonical_list: List[Dict[str, Any]]) -> CandidateProfile:
    """
    Merge a list of canonical source dicts into one CandidateProfile.

    This is the main merge function. It:
    1. Collects values for each field from all sources
    2. Resolves conflicts (scalar fields)
    3. Merges lists (list fields)
    4. Builds Skill objects with source tracking
    5. Returns a complete CandidateProfile

    Parameters:
        canonical_list (List[Dict]): List of canonical dicts from canonical_mapper.py
            Each dict has a "_source" key identifying where it came from.

    Returns:
        CandidateProfile: The merged, unified candidate profile
    """
    logger.info(f"Merging {len(canonical_list)} canonical sources...")

    # Create a new empty profile to fill in
    profile = CandidateProfile()

    # Track which sources we processed
    sources_processed = [c["_source"] for c in canonical_list if c.get("_source")]
    profile._sources_processed = sources_processed

    # ── 1. Merge full_name (scalar — conflict resolution) ─────────────
    name_candidates = [
        (c.get("full_name"), c.get("_source"))
        for c in canonical_list if c.get("full_name")
    ]
    profile.full_name = resolve_scalar(name_candidates) or ""

    # Generate candidate ID from the resolved name + first email
    # (done after email merge below, so we do it at the end)

    # ── 2. Merge emails (list — union) ────────────────────────────────
    all_emails = []
    for c in canonical_list:
        all_emails.extend(c.get("emails", []))
    profile.emails = deduplicate_emails(all_emails)

    # ── 3. Merge phones (list — union) ────────────────────────────────
    all_phones = []
    for c in canonical_list:
        all_phones.extend(c.get("phones", []))
    profile.phones = deduplicate_phones(all_phones)

    # ── 4. Merge location (special merge — best of each sub-field) ────
    location_candidates = [
        (c.get("location", {}), c.get("_source"))
        for c in canonical_list
    ]
    profile.location = merge_location(location_candidates)

    # ── 5. Merge links (take first non-None per link type) ────────────
    for c in canonical_list:
        links = c.get("links", {})
        if links.get("linkedin") and not profile.links.get("linkedin"):
            profile.links["linkedin"] = links["linkedin"]
        if links.get("github") and not profile.links.get("github"):
            profile.links["github"] = links["github"]
        if links.get("portfolio") and not profile.links.get("portfolio"):
            profile.links["portfolio"] = links["portfolio"]
        for other_url in links.get("other", []):
            if other_url not in profile.links["other"]:
                profile.links["other"].append(other_url)

    # ── 6. Merge headline (scalar — conflict resolution) ──────────────
    headline_candidates = [
        (c.get("headline"), c.get("_source"))
        for c in canonical_list if c.get("headline")
    ]
    profile.headline = resolve_scalar(headline_candidates)

    # ── 7. Merge years_experience (take from highest priority source) ─
    exp_candidates = [
        (c.get("years_experience"), c.get("_source"))
        for c in canonical_list if c.get("years_experience") is not None
    ]
    profile.years_experience = resolve_scalar(exp_candidates)

    # ── 8. Merge skills (union + source tracking) ─────────────────────
    # Build a dict: skill_name → set of sources that mention it
    skill_sources: Dict[str, set] = {}   # {"Java": {"Resume", "GitHub"}}

    for c in canonical_list:
        source = c.get("_source", "Unknown")
        for skill_name in c.get("skills", []):
            if not skill_name:
                continue
            # Use lowercase as the dedup key
            key = skill_name.lower()
            if key not in skill_sources:
                skill_sources[key] = {"name": skill_name, "sources": set()}
            skill_sources[key]["sources"].add(source)

    # Convert to Skill objects
    # We'll fill in confidence scores in the confidence_calculator module
    profile.skills = [
        Skill(
            name=data["name"],
            confidence=0.0,        # Placeholder — filled by confidence_calculator
            sources=list(data["sources"])
        )
        for data in skill_sources.values()
    ]

    # ── 9. Merge experience (union + dedup by company) ────────────────
    all_experience = []
    for c in canonical_list:
        for exp in c.get("experience", []):
            if exp and exp.get("company"):
                all_experience.append(exp)

    # Deduplicate
    deduped_exp = deduplicate_experience(all_experience)

    # Convert to Experience objects
    profile.experience = [
        Experience(
            company = exp.get("company", ""),
            title   = exp.get("title"),
            start   = exp.get("start"),
            end     = exp.get("end"),
            summary = exp.get("summary"),
        )
        for exp in deduped_exp
        if exp.get("company")
    ]

    # ── 10. Merge education (union + dedup by institution) ────────────
    all_education = []
    for c in canonical_list:
        for edu in c.get("education", []):
            if edu and edu.get("institution"):
                all_education.append(edu)

    deduped_edu = deduplicate_education(all_education)

    profile.education = [
        Education(
            institution = edu.get("institution", ""),
            degree      = edu.get("degree"),
            field       = edu.get("field"),
            start_year  = edu.get("start_year"),
            end_year    = edu.get("end_year"),
        )
        for edu in deduped_edu
        if edu.get("institution")
    ]

    # ── 11. Generate candidate ID now that we have name and email ──────
    first_email = profile.emails[0] if profile.emails else ""
    profile.candidate_id = generate_candidate_id(profile.full_name, first_email)

    logger.info(
        f"Merge complete — "
        f"name: {profile.full_name}, "
        f"emails: {len(profile.emails)}, "
        f"phones: {len(profile.phones)}, "
        f"skills: {len(profile.skills)}, "
        f"experience: {len(profile.experience)}, "
        f"education: {len(profile.education)}"
    )

    return profile
