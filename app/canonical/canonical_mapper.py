# app/canonical/canonical_mapper.py
#
# Maps parsed data from any source into the canonical schema.
# This is Module 4 of the assignment.
#
# Each source uses different field names:
#   Resume CSV   → "Candidate Name"
#   LinkedIn JSON → "firstName" + "lastName"
#   GitHub API   → "name"
#   ATS JSON     → "fullName"
#
# This mapper converts ALL of them to "full_name".
# After mapping, every source looks identical internally.

from typing import Dict, Any, List
from app.canonical.canonical_schema import create_empty_canonical
from app.normalizers.name_normalizer import normalize_name
from app.normalizers.email_normalizer import normalize_email
from app.normalizers.phone_normalizer import normalize_phone
from app.normalizers.skill_normalizer import normalize_skill
from app.normalizers.date_normalizer import normalize_date
from app.normalizers.location_normalizer import normalize_location
from app.parsers.github_parser import parse_github_location
from app.utils.logger import get_logger
from app.utils.constants import (
    SOURCE_RESUME, SOURCE_CSV, SOURCE_JSON,
    SOURCE_GITHUB, SOURCE_LINKEDIN, SOURCE_NOTES
)

logger = get_logger(__name__)


# ──────────────────────────────────────────────────────────────────────
# PUBLIC MAPPER FUNCTIONS
# One function per source type.
# All return a canonical dict (same shape as create_empty_canonical()).
# ──────────────────────────────────────────────────────────────────────

def map_resume_to_canonical(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert parsed resume data to canonical format.

    Parameters:
        parsed (Dict): Output from resume_parser.parse_resume()

    Returns:
        Dict: Canonical candidate data
    """
    logger.info("Mapping Resume data to canonical schema...")
    canon = create_empty_canonical()
    canon["_source"] = SOURCE_RESUME

    # ── Name ──────────────────────────────────────────────────────────
    if parsed.get("full_name"):
        canon["full_name"] = normalize_name(parsed["full_name"])

    # ── Emails ────────────────────────────────────────────────────────
    canon["emails"] = [
        normalize_email(e) for e in parsed.get("emails", [])
        if normalize_email(e)  # filter out invalid emails (empty string returned)
    ]

    # ── Phones ────────────────────────────────────────────────────────
    canon["phones"] = [
        normalize_phone(p) for p in parsed.get("phones", [])
        if p
    ]

    # ── Links ─────────────────────────────────────────────────────────
    if parsed.get("linkedin"):
        canon["links"]["linkedin"] = parsed["linkedin"]
    if parsed.get("github"):
        canon["links"]["github"] = parsed["github"]
    if parsed.get("portfolio"):
        canon["links"]["portfolio"] = parsed["portfolio"]

    # ── Headline ──────────────────────────────────────────────────────
    if parsed.get("headline"):
        canon["headline"] = parsed["headline"]

    # ── Skills ────────────────────────────────────────────────────────
    # normalize_skill() cleans each skill name
    # filter(None, ...) removes any that came back as empty string
    canon["skills"] = list(filter(None, [
        normalize_skill(s) for s in parsed.get("skills", [])
        if s and len(s.strip()) > 1
    ]))

    # ── Experience (raw text lines → structured) ──────────────────────
    # Resume experience is raw lines — we do a basic structure extraction
    exp_lines = parsed.get("experience_raw", [])
    canon["experience"] = _parse_experience_lines(exp_lines)

    # ── Education (raw text lines → structured) ───────────────────────
    edu_lines = parsed.get("education_raw", [])
    canon["education"] = _parse_education_lines(edu_lines)

    return canon


def map_csv_to_canonical(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert one CSV row (dict) to canonical format.

    CSV column names vary — we try multiple possible column names.
    _get() is our helper that checks multiple field name variants.

    Parameters:
        row (Dict): One row from the CSV, keys = column headers

    Returns:
        Dict: Canonical candidate data
    """
    logger.info("Mapping CSV row to canonical schema...")
    canon = create_empty_canonical()
    canon["_source"] = SOURCE_CSV

    # _get(row, [...]) tries each key in the list and returns the first match
    name = _get(row, ["full_name", "name", "candidate name", "candidate_name", "fullname"])
    if name:
        canon["full_name"] = normalize_name(name)

    email = _get(row, ["email", "email_address", "email address", "e-mail"])
    if email:
        valid_email = normalize_email(email)
        if valid_email:
            canon["emails"] = [valid_email]

    phone = _get(row, ["phone", "phone_number", "phone number", "mobile", "contact"])
    if phone:
        canon["phones"] = [normalize_phone(phone)]

    # Location fields
    city    = _get(row, ["city", "town"])
    region  = _get(row, ["state", "region", "province"])
    country = _get(row, ["country", "country_code"])
    if city or region or country:
        canon["location"] = normalize_location(city or "", region or "", country or "")

    # Skills (might be a comma-separated string or already a list)
    skills_raw = _get(row, ["skills", "skill_set", "technologies", "tech_stack"])
    if skills_raw:
        if isinstance(skills_raw, str):
            # Split by comma, semicolon, or pipe
            import re
            skills_list = re.split(r"[,;|]", skills_raw)
        else:
            skills_list = skills_raw
        canon["skills"] = list(filter(None, [normalize_skill(s) for s in skills_list if s]))

    # Headline / Title
    headline = _get(row, ["headline", "title", "designation", "role", "job_title"])
    if headline:
        canon["headline"] = headline.strip()

    # Links
    linkedin = _get(row, ["linkedin", "linkedin_url", "linkedin_profile"])
    if linkedin:
        canon["links"]["linkedin"] = linkedin

    github = _get(row, ["github", "github_url", "github_profile"])
    if github:
        canon["links"]["github"] = github

    return canon


def map_json_to_canonical(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert an ATS JSON export to canonical format.

    JSON exports from ATS systems use camelCase field names.

    Parameters:
        data (Dict): Output from json_extractor.extract_from_json()

    Returns:
        Dict: Canonical candidate data
    """
    logger.info("Mapping JSON data to canonical schema...")
    canon = create_empty_canonical()
    canon["_source"] = SOURCE_JSON

    # Name — try camelCase and snake_case variants
    name = _get(data, ["fullName", "full_name", "name", "candidateName"])
    if name:
        canon["full_name"] = normalize_name(name)

    # Email
    email = _get(data, ["email", "emailAddress", "email_address"])
    if email:
        valid = normalize_email(email)
        if valid:
            canon["emails"] = [valid]

    # Phone
    phone = _get(data, ["phone", "phoneNumber", "phone_number", "mobile"])
    if phone:
        canon["phones"] = [normalize_phone(str(phone))]

    # Location
    location = data.get("location", {})
    if isinstance(location, dict):
        city    = location.get("city", "")
        region  = location.get("state", "") or location.get("region", "")
        country = location.get("country", "")
        canon["location"] = normalize_location(city, region, country)

    # Headline
    headline = _get(data, ["headline", "title", "designation", "jobTitle"])
    if headline:
        canon["headline"] = headline

    # Skills
    skills = data.get("skills", [])
    if isinstance(skills, list):
        canon["skills"] = list(filter(None, [
            normalize_skill(s if isinstance(s, str) else s.get("name", ""))
            for s in skills
        ]))

    # Experience
    experience = data.get("experience", data.get("workHistory", []))
    if isinstance(experience, list):
        canon["experience"] = [_map_json_experience(exp) for exp in experience]

    # Education
    education = data.get("education", [])
    if isinstance(education, list):
        canon["education"] = [_map_json_education(edu) for edu in education]

    # Links
    links = data.get("links", {})
    if isinstance(links, dict):
        canon["links"]["linkedin"]  = links.get("linkedin")
        canon["links"]["github"]    = links.get("github")
        canon["links"]["portfolio"] = links.get("portfolio")

    return canon


def map_github_to_canonical(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert parsed GitHub data to canonical format.

    Parameters:
        parsed (Dict): Output from github_parser.parse_github()

    Returns:
        Dict: Canonical candidate data
    """
    logger.info("Mapping GitHub data to canonical schema...")
    canon = create_empty_canonical()
    canon["_source"] = SOURCE_GITHUB

    if parsed.get("full_name"):
        canon["full_name"] = normalize_name(parsed["full_name"])

    for email in parsed.get("emails", []):
        valid = normalize_email(email)
        if valid:
            canon["emails"].append(valid)

    if parsed.get("github"):
        canon["links"]["github"] = parsed["github"]

    if parsed.get("headline"):
        canon["headline"] = parsed["headline"]

    canon["skills"] = list(filter(None, [
        normalize_skill(s) for s in parsed.get("skills", []) if s
    ]))

    # Parse the free-text location
    if parsed.get("location_raw"):
        loc = parse_github_location(parsed["location_raw"])
        canon["location"] = normalize_location(
            loc.get("city", ""),
            loc.get("region", ""),
            loc.get("country", "")
        )

    return canon


def map_linkedin_to_canonical(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert parsed LinkedIn data to canonical format.

    Parameters:
        parsed (Dict): Output from linkedin_parser.parse_linkedin()

    Returns:
        Dict: Canonical candidate data
    """
    logger.info("Mapping LinkedIn data to canonical schema...")
    canon = create_empty_canonical()
    canon["_source"] = SOURCE_LINKEDIN

    if parsed.get("full_name"):
        canon["full_name"] = normalize_name(parsed["full_name"])

    for email in parsed.get("emails", []):
        valid = normalize_email(email)
        if valid:
            canon["emails"].append(valid)

    for phone in parsed.get("phones", []):
        if phone:
            canon["phones"].append(normalize_phone(phone))

    if parsed.get("linkedin"):
        canon["links"]["linkedin"] = parsed["linkedin"]

    if parsed.get("github"):
        canon["links"]["github"] = parsed["github"]

    if parsed.get("headline"):
        canon["headline"] = parsed["headline"]

    canon["skills"] = list(filter(None, [
        normalize_skill(s) for s in parsed.get("skills", []) if s
    ]))

    # Location
    if parsed.get("location_raw"):
        loc = parse_github_location(parsed["location_raw"])  # reuse same splitter
        canon["location"] = normalize_location(
            loc.get("city", ""),
            loc.get("region", ""),
            loc.get("country", "")
        )

    # Experience from LinkedIn JSON export
    for exp in parsed.get("experience_raw", []):
        if isinstance(exp, dict):
            canon["experience"].append(_map_linkedin_experience(exp))

    # Education from LinkedIn JSON export
    for edu in parsed.get("education_raw", []):
        if isinstance(edu, dict):
            canon["education"].append(_map_linkedin_education(edu))

    return canon


def map_notes_to_canonical(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert parsed recruiter notes to canonical format.

    Parameters:
        parsed (Dict): Output from notes_parser.parse_notes()

    Returns:
        Dict: Canonical candidate data (sparse — notes don't have all fields)
    """
    logger.info("Mapping Notes data to canonical schema...")
    canon = create_empty_canonical()
    canon["_source"] = SOURCE_NOTES

    for email in parsed.get("emails", []):
        valid = normalize_email(email)
        if valid:
            canon["emails"].append(valid)

    for phone in parsed.get("phones", []):
        if phone:
            canon["phones"].append(normalize_phone(phone))

    if parsed.get("headline"):
        canon["headline"] = parsed["headline"]

    canon["skills"] = list(filter(None, [
        normalize_skill(s) for s in parsed.get("skills", []) if s
    ]))

    # Companies from notes become sparse experience entries
    for company in parsed.get("companies_raw", []):
        if company:
            canon["experience"].append({
                "company": company,
                "title":   None,
                "start":   None,
                "end":     None,
                "summary": parsed.get("summary"),
            })

    return canon


# ──────────────────────────────────────────────────────────────────────
# PRIVATE HELPER FUNCTIONS
# ──────────────────────────────────────────────────────────────────────

def _get(data: Dict, keys: List[str]) -> Any:
    """
    Try multiple key names and return the first non-empty value found.
    Case-insensitive: tries exact key first, then lowercase version.

    This handles the fact that different sources use different field names.
    """
    for key in keys:
        # Try exact case
        if key in data and data[key]:
            return data[key]
        # Try lowercase key against lowercase dict keys
        for data_key, data_val in data.items():
            if data_key.lower() == key.lower() and data_val:
                return data_val
    return None


def _parse_experience_lines(lines: List[str]) -> List[Dict]:
    """
    Convert raw resume experience text lines into structured experience dicts.
    This is a heuristic parser — it makes best-effort guesses.
    """
    import re
    experiences = []
    current = {}

    for line in lines:
        # Date pattern: "Jan 2022 - Present" or "2022 - 2025"
        date_match = re.search(
            r"(\w+\s+\d{4}|\d{4})\s*[-–to]+\s*(\w+\s+\d{4}|\d{4}|present|current)",
            line, re.IGNORECASE
        )
        if date_match:
            if current:
                experiences.append(current)
            current = {
                "start": normalize_date(date_match.group(1)),
                "end":   normalize_date(date_match.group(2)),
                "company": None, "title": None, "summary": None
            }
        elif current and not current.get("company") and len(line.split()) <= 5:
            current["company"] = line
        elif current and not current.get("title") and len(line.split()) <= 6:
            current["title"] = line
        elif current:
            # Accumulate as summary
            current["summary"] = (current.get("summary") or "") + " " + line

    if current:
        experiences.append(current)

    return experiences


def _parse_education_lines(lines: List[str]) -> List[Dict]:
    """
    Convert raw resume education text lines into structured education dicts.
    """
    import re
    educations = []
    current = {}

    for line in lines:
        # Year: 4 digits
        year_match = re.search(r"\b(20\d{2}|19\d{2})\b", line)
        if not current:
            current = {
                "institution": line,
                "degree": None, "field": None,
                "start_year": None, "end_year": None
            }
        elif not current.get("degree") and any(
            d in line.lower() for d in ["b.e", "b.tech", "m.tech", "m.e", "b.sc", "m.sc", "phd", "mba", "b.com"]
        ):
            current["degree"] = line
        elif year_match:
            year = int(year_match.group(1))
            if not current.get("start_year"):
                current["start_year"] = year
            else:
                current["end_year"] = year
            educations.append(current)
            current = {}

    if current and current.get("institution"):
        educations.append(current)

    return educations


def _map_json_experience(exp: Dict) -> Dict:
    """Map a JSON experience object to canonical experience format."""
    return {
        "company": exp.get("company", exp.get("companyName", "")),
        "title":   exp.get("title", exp.get("jobTitle", exp.get("role", ""))),
        "start":   normalize_date(exp.get("startDate", exp.get("start", ""))),
        "end":     normalize_date(exp.get("endDate", exp.get("end", ""))),
        "summary": exp.get("description", exp.get("summary", "")),
    }


def _map_json_education(edu: Dict) -> Dict:
    """Map a JSON education object to canonical education format."""
    return {
        "institution": edu.get("institution", edu.get("school", edu.get("college", ""))),
        "degree":      edu.get("degree", edu.get("degreeName", "")),
        "field":       edu.get("field", edu.get("fieldOfStudy", edu.get("major", ""))),
        "start_year":  edu.get("startYear", edu.get("start_year")),
        "end_year":    edu.get("endYear", edu.get("end_year")),
    }


def _map_linkedin_experience(exp: Dict) -> Dict:
    """Map a LinkedIn experience object to canonical format."""
    return {
        "company": exp.get("companyName", exp.get("company", "")),
        "title":   exp.get("title", ""),
        "start":   normalize_date(str(exp.get("startDate", ""))),
        "end":     normalize_date(str(exp.get("endDate", ""))) if exp.get("endDate") else "Present",
        "summary": exp.get("description", ""),
    }


def _map_linkedin_education(edu: Dict) -> Dict:
    """Map a LinkedIn education object to canonical format."""
    return {
        "institution": edu.get("schoolName", edu.get("institution", "")),
        "degree":      edu.get("degreeName", edu.get("degree", "")),
        "field":       edu.get("fieldOfStudy", edu.get("field", "")),
        "start_year":  edu.get("startDate", {}).get("year") if isinstance(edu.get("startDate"), dict) else None,
        "end_year":    edu.get("endDate", {}).get("year") if isinstance(edu.get("endDate"), dict) else None,
    }
