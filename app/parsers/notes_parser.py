# app/parsers/notes_parser.py
#
# Parses recruiter notes (plain text) to extract candidate information.
# Notes are the most freeform input — they're written by humans in natural language.
# Example: "John has excellent communication. Worked at Infosys. Knows Java."
# We use keyword-based matching and regex to extract what we can.

import re
from typing import Dict, Any, List
from app.utils.logger import get_logger
from app.utils.helper import clean_text

logger = get_logger(__name__)

# Keywords that precede a company name in recruiter notes
COMPANY_KEYWORDS = [
    "worked at", "working at", "employed at", "employed by",
    "currently at", "at", "joined", "ex-", "ex ", "previously at",
]

# Keywords that indicate a skill mention
SKILL_KEYWORDS = ["knows", "experience in", "skilled in", "expertise in", "proficient in", "familiar with"]

# Known company names — used for fallback detection
KNOWN_COMPANIES = [
    "infosys", "tcs", "wipro", "accenture", "cognizant", "capgemini",
    "amazon", "google", "microsoft", "apple", "meta", "ibm", "oracle",
    "hcl", "tech mahindra", "deloitte", "kpmg", "pwc",
]

# Known skill names (same list as in resume_parser for consistency)
KNOWN_SKILLS = [
    "java", "python", "javascript", "typescript", "c++", "c#", "go", "rust",
    "spring boot", "django", "flask", "fastapi", "react", "angular", "vue",
    "node.js", "mysql", "postgresql", "mongodb", "redis", "oracle",
    "aws", "azure", "gcp", "docker", "kubernetes", "jenkins", "git",
    "html", "css", "sql", "rest api", "graphql", "linux",
]


def parse_notes(text: str) -> Dict[str, Any]:
    """
    Extract candidate information from recruiter notes.

    Parameters:
        text (str): Raw recruiter notes

    Returns:
        Dict: Extracted fields (most will be None or empty as notes are sparse)
    """
    logger.info("Parsing recruiter notes...")

    result = {
        "full_name":      None,
        "emails":         [],
        "phones":         [],
        "skills":         [],
        "headline":       None,
        "companies_raw":  [],
        "summary":        None,
    }

    if not text:
        return result

    # ── Emails and Phones ────────────────────────────────────────────
    emails = re.findall(r"[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}", text)
    result["emails"] = list(set(emails))

    phones = re.findall(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", text)
    result["phones"] = [p for p in phones if len(re.sub(r"\D", "", p)) >= 10]

    # ── Extract skills mentioned in notes ────────────────────────────
    text_lower = text.lower()

    # Method 1: After skill keywords ("knows Java", "experience in Python")
    skills_found = set()
    for keyword in SKILL_KEYWORDS:
        # Find text after skill keywords
        # re.findall with capture group returns the captured part
        pattern = rf"{re.escape(keyword)}\s+([\w\s,+#.]+?)(?:[.\n]|$)"
        matches = re.findall(pattern, text_lower, re.IGNORECASE)
        for match in matches:
            # Split on commas and "and"
            items = re.split(r",|\band\b", match)
            for item in items:
                item = clean_text(item)
                if item:
                    skills_found.add(item)

    # Method 2: Scan for known skill keywords anywhere in the text
    for skill in KNOWN_SKILLS:
        if skill in text_lower:
            # Get proper case version from our skill list
            skills_found.add(skill)

    result["skills"] = list(skills_found)

    # ── Extract company names ─────────────────────────────────────────
    companies = set()

    # Method 1: After company keywords ("worked at Infosys")
    for keyword in COMPANY_KEYWORDS:
        pattern = rf"{re.escape(keyword)}\s+([A-Z][a-zA-Z\s]+?)(?:[.\n,]|$)"
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            companies.add(clean_text(match))

    # Method 2: Known companies
    for company in KNOWN_COMPANIES:
        if company in text_lower:
            companies.add(company.title())

    result["companies_raw"] = list(companies)

    # ── Headline detection ────────────────────────────────────────────
    # Look for patterns like "Senior Developer", "Backend Engineer" in notes
    title_pattern = r"(?:is a|is an|works as|as a|as an)\s+([\w\s]+(?:developer|engineer|analyst|manager|designer|architect|lead|consultant))"
    title_match = re.search(title_pattern, text, re.IGNORECASE)
    if title_match:
        result["headline"] = clean_text(title_match.group(1)).title()

    # ── Store raw notes as summary ────────────────────────────────────
    # The full notes text is useful context — we store it as summary
    result["summary"] = clean_text(text)

    logger.info(
        f"Notes parsed — skills: {len(result['skills'])}, "
        f"companies: {len(result['companies_raw'])}"
    )
    return result
