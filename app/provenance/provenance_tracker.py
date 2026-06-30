# app/provenance/provenance_tracker.py
#
# Module 10: Provenance Tracking
#
# "Provenance" = the origin/history of a piece of data.
# For every field in the final profile, we record:
#   - Which field it is (e.g. "full_name")
#   - Where it came from (e.g. "Resume")
#   - How it was obtained (e.g. "Direct Extraction", "Text Parsing", "Merged")
#
# This builds the "provenance" array in the final JSON output.

from typing import List, Dict, Any
from app.models.candidate  import CandidateProfile
from app.models.provenance import ProvenanceRecord
from app.merger.conflict_resolver import resolve_winner_source, get_source_priority
from app.utils.logger import get_logger

logger = get_logger(__name__)


def build_provenance(
    profile: CandidateProfile,
    canonical_list: List[Dict[str, Any]]
) -> CandidateProfile:
    """
    Build provenance records for every field in the profile.

    For each field, we determine:
    1. Which source(s) provided the value
    2. What method was used (Direct Extraction, Text Parsing, API, Merged, etc.)

    Parameters:
        profile        (CandidateProfile): The merged profile
        canonical_list (List[Dict]):       All canonical source dicts

    Returns:
        CandidateProfile: Profile with provenance list filled in
    """
    logger.info("Building provenance records...")
    records = []

    # ── Helper: find which source provided a scalar field ─────────────
    def find_source_for_field(field_name: str) -> str:
        """
        Find the highest-priority source that provided a value for field_name.
        """
        candidates = [
            (c.get(field_name), c.get("_source"))
            for c in canonical_list
            if c.get(field_name)
        ]
        return resolve_winner_source(candidates) or "Unknown"

    # ── Helper: determine the extraction method for a source ──────────
    def get_method(source: str) -> str:
        """
        Return a human-readable extraction method name for a source.
        """
        method_map = {
            "Resume":   "Text Parsing",
            "CSV":      "Direct Extraction",
            "JSON":     "Direct Extraction",
            "GitHub":   "API + Repository Analysis",
            "LinkedIn": "Profile Parsing",
            "Notes":    "Text Parsing",
        }
        return method_map.get(source, "Direct Extraction")

    # ── full_name provenance ───────────────────────────────────────────
    if profile.full_name:
        source = find_source_for_field("full_name")
        records.append(ProvenanceRecord(
            field="full_name",
            value=profile.full_name,
            source=source,
            method=get_method(source)
        ))

    # ── emails provenance ─────────────────────────────────────────────
    if profile.emails:
        # Find which source provided emails
        email_sources = [
            c.get("_source") for c in canonical_list
            if c.get("emails")
        ]
        source_str = " + ".join(email_sources) if len(email_sources) > 1 else (email_sources[0] if email_sources else "Unknown")
        records.append(ProvenanceRecord(
            field="emails",
            value=", ".join(profile.emails),
            source=source_str,
            method="Direct Extraction" if len(email_sources) <= 1 else "Merged"
        ))

    # ── phones provenance ─────────────────────────────────────────────
    if profile.phones:
        phone_sources = [
            c.get("_source") for c in canonical_list
            if c.get("phones")
        ]
        source_str = " + ".join(phone_sources) if len(phone_sources) > 1 else (phone_sources[0] if phone_sources else "Unknown")
        records.append(ProvenanceRecord(
            field="phones",
            value=", ".join(profile.phones),
            source=source_str,
            method="Direct Extraction" if len(phone_sources) <= 1 else "Merged"
        ))

    # ── headline provenance ───────────────────────────────────────────
    if profile.headline:
        source = find_source_for_field("headline")
        records.append(ProvenanceRecord(
            field="headline",
            value=profile.headline,
            source=source,
            method=get_method(source)
        ))

    # ── skills provenance ─────────────────────────────────────────────
    # Skills come from multiple sources, so we record the merge
    skill_source_names = set()
    for skill in profile.skills:
        skill_source_names.update(skill.sources)

    if skill_source_names:
        source_str = " + ".join(sorted(skill_source_names))
        method = "Merged" if len(skill_source_names) > 1 else "Direct Extraction"
        records.append(ProvenanceRecord(
            field="skills",
            value=f"{len(profile.skills)} skills",
            source=source_str,
            method=method
        ))

    # ── experience provenance ─────────────────────────────────────────
    if profile.experience:
        exp_sources = [
            c.get("_source") for c in canonical_list
            if c.get("experience")
        ]
        source_str = " + ".join(exp_sources) if len(exp_sources) > 1 else (exp_sources[0] if exp_sources else "Unknown")
        records.append(ProvenanceRecord(
            field="experience",
            value=f"{len(profile.experience)} entries",
            source=source_str,
            method="Merged" if len(exp_sources) > 1 else get_method(source_str)
        ))

    # ── education provenance ──────────────────────────────────────────
    if profile.education:
        edu_sources = [
            c.get("_source") for c in canonical_list
            if c.get("education")
        ]
        source_str = " + ".join(edu_sources) if len(edu_sources) > 1 else (edu_sources[0] if edu_sources else "Unknown")
        records.append(ProvenanceRecord(
            field="education",
            value=f"{len(profile.education)} entries",
            source=source_str,
            method="Merged" if len(edu_sources) > 1 else get_method(source_str)
        ))

    # ── location provenance ───────────────────────────────────────────
    if any(profile.location.values()):
        loc_sources = [
            c.get("_source") for c in canonical_list
            if any((c.get("location") or {}).values())
        ]
        source_str = loc_sources[0] if loc_sources else "Unknown"
        records.append(ProvenanceRecord(
            field="location",
            source=source_str,
            method=get_method(source_str)
        ))

    profile.provenance = records

    logger.info(f"Provenance built — {len(records)} records created")
    return profile
