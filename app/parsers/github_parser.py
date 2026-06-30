from typing import Dict, Any
from app.utils.logger import get_logger
from app.utils.helper import clean_text

logger = get_logger(__name__)


def parse_github(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """Map GitHub API response fields to the intermediate parsed format."""
    logger.info("Parsing GitHub data...")

    result = {
        "full_name": None, "emails": [], "phones": [],
        "linkedin": None, "github": raw_data.get("html_url"),
        "portfolio": None, "skills": [], "headline": None, "location_raw": None,
    }

    if not raw_data:
        return result

    if raw_data.get("name"):
        result["full_name"] = raw_data["name"].strip()

    if raw_data.get("email"):
        result["emails"] = [raw_data["email"]]

    if raw_data.get("bio"):
        result["headline"] = clean_text(raw_data["bio"])

    if raw_data.get("location"):
        result["location_raw"] = raw_data["location"]

    # GitHub language list → treated as skills
    result["skills"] = [lang for lang in raw_data.get("languages", []) if lang]

    logger.info(f"GitHub parsed — name: {result['full_name']}, skills: {len(result['skills'])}")
    return result


def parse_github_location(location_str: str) -> Dict[str, str]:
    """Split a free-text GitHub location string into city, region, country by comma."""
    if not location_str:
        return {"city": "", "region": "", "country": ""}

    parts = [p.strip() for p in location_str.split(",")]

    if len(parts) == 1:
        return {"city": "", "region": "", "country": parts[0]}
    elif len(parts) == 2:
        return {"city": parts[0], "region": "", "country": parts[1]}
    else:
        return {"city": parts[0], "region": parts[-2], "country": parts[-1]}
