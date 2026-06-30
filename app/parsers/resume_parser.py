import re
from typing import Dict, Any, List
from app.utils.logger import get_logger
from app.utils.helper import clean_text

logger = get_logger(__name__)

EMAIL_PATTERN    = r"[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}"
PHONE_PATTERN    = r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}"
LINKEDIN_PATTERN = r"(?:https?://)?(?:www\.)?linkedin\.com/in/[\w-]+"
GITHUB_PATTERN   = r"(?:https?://)?(?:www\.)?github\.com/[\w-]+"

SECTION_HEADERS = {
    "skills":       ["skills", "technical skills", "core skills", "key skills", "technologies"],
    "experience":   ["experience", "work experience", "employment", "professional experience", "work history"],
    "education":    ["education", "academic", "qualification", "academics"],
    "projects":     ["projects", "personal projects", "academic projects"],
    "certifications": ["certifications", "certificates", "awards"],
}

# Fallback skill list used when no skills section is found in the resume
KNOWN_SKILLS = [
    "java", "python", "javascript", "typescript", "c++", "c#", "go", "rust", "kotlin", "swift",
    "spring boot", "django", "flask", "fastapi", "react", "angular", "vue",
    "node.js", "nodejs", "express",
    "mysql", "postgresql", "mongodb", "redis", "oracle",
    "aws", "azure", "gcp", "docker", "kubernetes", "jenkins", "git",
    "html", "css", "sql", "rest api", "graphql", "linux", "maven", "gradle",
    "hibernate", "jpa", "spring", "pandas", "numpy", "tensorflow", "pytorch",
]


def parse_resume(text: str) -> Dict[str, Any]:
    """Extract structured fields from raw resume text using regex and heuristics."""
    logger.info("Parsing resume text...")

    result = {
        "full_name": None, "emails": [], "phones": [],
        "linkedin": None, "github": None, "portfolio": None,
        "skills": [], "experience_raw": [], "education_raw": [], "headline": None,
    }

    if not text:
        logger.warning("Resume text is empty")
        return result

    lines = [clean_text(line) for line in text.split("\n") if clean_text(line)]

    result["emails"] = list(set(re.findall(EMAIL_PATTERN, text, re.IGNORECASE)))

    phones = re.findall(PHONE_PATTERN, text)
    result["phones"] = [p for p in phones if len(re.sub(r"\D", "", p)) >= 10]

    linkedin_matches = re.findall(LINKEDIN_PATTERN, text, re.IGNORECASE)
    if linkedin_matches:
        url = linkedin_matches[0]
        result["linkedin"] = url if url.startswith("http") else f"https://{url}"

    github_matches = re.findall(GITHUB_PATTERN, text, re.IGNORECASE)
    if github_matches:
        url = github_matches[0]
        result["github"] = url if url.startswith("http") else f"https://{url}"

    # Name heuristic: first 2-4 Title Case words without digits or @ in first 5 lines
    for line in lines[:5]:
        words = line.split()
        if (2 <= len(words) <= 4 and "@" not in line
                and not re.search(r"\d", line)
                and all(w[0].isupper() for w in words if w)):
            result["full_name"] = line
            break

    # Headline heuristic: short line immediately after the name line
    name_found = False
    for line in lines[:8]:
        if result["full_name"] and line == result["full_name"]:
            name_found = True
            continue
        if name_found and len(line.split()) <= 6 and "@" not in line and not re.search(r"\d{5,}", line):
            result["headline"] = line
            break

    skills_section = _extract_section(text, "skills")
    if skills_section:
        raw_items = re.split(r"[,|\n•·▪►✓\-]", skills_section)
        result["skills"] = [clean_text(s) for s in raw_items if len(clean_text(s)) > 1]
    else:
        text_lower = text.lower()
        result["skills"] = [
            skill.title() if not any(c.isupper() for c in skill) else skill
            for skill in KNOWN_SKILLS if skill in text_lower
        ]

    exp_section = _extract_section(text, "experience")
    if exp_section:
        result["experience_raw"] = [clean_text(l) for l in exp_section.split("\n") if len(clean_text(l)) > 3]

    edu_section = _extract_section(text, "education")
    if edu_section:
        result["education_raw"] = [clean_text(l) for l in edu_section.split("\n") if len(clean_text(l)) > 3]

    logger.info(f"Resume parsed — name: {result['full_name']}, emails: {len(result['emails'])}, skills: {len(result['skills'])}")
    return result


def _extract_section(text: str, section: str) -> str:
    """Collect lines between a section header and the next known section header."""
    headers_to_find = SECTION_HEADERS.get(section, [])
    all_headers = [h for headers in SECTION_HEADERS.values() for h in headers]
    lines = text.split("\n")
    inside = False
    collected = []

    for line in lines:
        line_lower = line.strip().lower()
        if any(line_lower == h or line_lower.startswith(h) for h in headers_to_find):
            inside = True
            continue
        if inside:
            if any(line_lower == h or line_lower.startswith(h) for h in all_headers if h not in headers_to_find):
                break
            collected.append(line)

    return "\n".join(collected).strip()
