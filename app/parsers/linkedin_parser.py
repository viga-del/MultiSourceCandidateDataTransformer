import re
from typing import Dict, Any
from app.utils.logger import get_logger
from app.utils.helper import clean_text

logger = get_logger(__name__)


def parse_linkedin(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse LinkedIn data into the intermediate format.
    Handles both JSON export (firstName/lastName keys) and plain text (raw_text key).
    """
    logger.info("Parsing LinkedIn data...")

    result = {
        "full_name": None, "emails": [], "phones": [],
        "linkedin": None, "github": None, "portfolio": None,
        "skills": [], "headline": None,
        "experience_raw": [], "education_raw": [], "location_raw": None,
    }

    if not raw_data:
        return result

    if "raw_text" in raw_data:
        return _parse_linkedin_text(raw_data["raw_text"])

    first = raw_data.get("firstName", "").strip()
    last  = raw_data.get("lastName", "").strip()
    if first or last:
        result["full_name"] = f"{first} {last}".strip()

    if raw_data.get("headline"):
        result["headline"] = clean_text(raw_data["headline"])

    email = raw_data.get("emailAddress", "") or raw_data.get("email", "")
    if email:
        result["emails"] = [email]

    phone = raw_data.get("phoneNumbers", [])
    if isinstance(phone, list):
        result["phones"] = [p.get("number", "") for p in phone if p.get("number")]
    elif isinstance(phone, str):
        result["phones"] = [phone]

    location = raw_data.get("location", {})
    if isinstance(location, dict):
        city    = location.get("city", "") or location.get("name", "")
        country = location.get("country", "") or location.get("countryCode", "")
        result["location_raw"] = f"{city}, {country}".strip(", ")
    elif isinstance(location, str):
        result["location_raw"] = location

    profile_url = raw_data.get("profileURL", "") or raw_data.get("publicProfileUrl", "")
    if profile_url:
        result["linkedin"] = profile_url

    for s in raw_data.get("skills", []):
        name = s.get("name", "") if isinstance(s, dict) else s
        if name:
            result["skills"].append(name)

    for exp in raw_data.get("experience", raw_data.get("positions", [])):
        if isinstance(exp, dict):
            result["experience_raw"].append(exp)

    for edu in raw_data.get("education", []):
        if isinstance(edu, dict):
            result["education_raw"].append(edu)

    logger.info(f"LinkedIn parsed — name: {result['full_name']}, skills: {len(result['skills'])}")
    return result


def _parse_linkedin_text(text: str) -> Dict[str, Any]:
    """Parse a plain text LinkedIn profile paste using regex (same approach as resume parser)."""
    logger.info("Parsing LinkedIn plain text...")

    result = {
        "full_name": None, "emails": [], "phones": [],
        "linkedin": None, "github": None, "portfolio": None,
        "skills": [], "headline": None,
        "experience_raw": [], "education_raw": [], "location_raw": None,
    }

    if not text:
        return result

    lines = [clean_text(line) for line in text.split("\n") if clean_text(line)]

    result["emails"] = list(set(re.findall(r"[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}", text)))

    phones = re.findall(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", text)
    result["phones"] = [p for p in phones if len(re.sub(r"\D", "", p)) >= 10]

    linkedin_matches = re.findall(r"(?:https?://)?(?:www\.)?linkedin\.com/in/[\w-]+", text, re.IGNORECASE)
    if linkedin_matches:
        url = linkedin_matches[0]
        result["linkedin"] = url if url.startswith("http") else f"https://{url}"

    for line in lines[:5]:
        words = line.split()
        if (2 <= len(words) <= 4 and "@" not in line
                and not re.search(r"\d", line)
                and all(w[0].isupper() for w in words if w)):
            result["full_name"] = line
            break

    name_seen = False
    for line in lines[:8]:
        if result["full_name"] and line == result["full_name"]:
            name_seen = True
            continue
        if name_seen and 1 <= len(line.split()) <= 8:
            result["headline"] = line
            break

    return result
