# app/normalizers/skill_normalizer.py
#
# Normalizes skill names so duplicates are detected correctly.
# Example: "JAVA", "java", "Java" are all the same skill.
# Example: "springboot", "Spring Boot", "spring-boot" are the same skill.

from app.utils.logger import get_logger

logger = get_logger(__name__)

# ──────────────────────────────────────────────────────────────────────
# SKILL ALIAS MAP
# Maps raw/variant names to their canonical form.
# Key: lowercase variant   Value: proper display name
#
# This map handles common misspellings and abbreviations.
# You can extend this map as needed.
# ──────────────────────────────────────────────────────────────────────
SKILL_ALIASES = {
    # Java ecosystem
    "java":           "Java",
    "springboot":     "Spring Boot",
    "spring boot":    "Spring Boot",
    "spring-boot":    "Spring Boot",
    "spring":         "Spring",
    "springmvc":      "Spring MVC",
    "spring mvc":     "Spring MVC",
    "hibernate":      "Hibernate",
    "jpa":            "JPA",
    "maven":          "Maven",
    "gradle":         "Gradle",

    # Python ecosystem
    "python":         "Python",
    "django":         "Django",
    "flask":          "Flask",
    "fastapi":        "FastAPI",
    "pandas":         "Pandas",
    "numpy":          "NumPy",

    # JavaScript ecosystem
    "javascript":     "JavaScript",
    "js":             "JavaScript",
    "typescript":     "TypeScript",
    "ts":             "TypeScript",
    "nodejs":         "Node.js",
    "node.js":        "Node.js",
    "node js":        "Node.js",
    "react":          "React",
    "reactjs":        "React",
    "angular":        "Angular",
    "vue":            "Vue.js",
    "vuejs":          "Vue.js",

    # Databases
    "mysql":          "MySQL",
    "postgresql":     "PostgreSQL",
    "postgres":       "PostgreSQL",
    "mongodb":        "MongoDB",
    "redis":          "Redis",
    "oracle":         "Oracle",
    "mssql":          "MSSQL",
    "sql server":     "MSSQL",

    # Cloud & DevOps
    "aws":            "AWS",
    "amazon web services": "AWS",
    "azure":          "Azure",
    "gcp":            "GCP",
    "google cloud":   "GCP",
    "docker":         "Docker",
    "kubernetes":     "Kubernetes",
    "k8s":            "Kubernetes",
    "jenkins":        "Jenkins",
    "git":            "Git",
    "github":         "GitHub",
    "gitlab":         "GitLab",
    "cicd":           "CI/CD",
    "ci/cd":          "CI/CD",

    # Other
    "rest":           "REST API",
    "rest api":       "REST API",
    "restful":        "REST API",
    "graphql":        "GraphQL",
    "sql":            "SQL",
    "html":           "HTML",
    "css":            "CSS",
    "c++":            "C++",
    "c#":             "C#",
    "golang":         "Go",
    "go":             "Go",
    "rust":           "Rust",
    "kotlin":         "Kotlin",
    "swift":          "Swift",
    "linux":          "Linux",
}


def normalize_skill(raw_skill: str) -> str:
    """
    Normalize a skill name to its canonical form.

    Steps:
    1. Strip whitespace
    2. Look up the lowercase version in SKILL_ALIASES
    3. If found, return the canonical name
    4. If not found, return Title Case version of the input

    Parameters:
        raw_skill (str): Skill name in any format

    Returns:
        str: Canonical skill name

    Examples:
        "JAVA"        → "Java"
        "springboot"  → "Spring Boot"
        "NODEJS"      → "Node.js"
        "TensorFlow"  → "TensorFlow"  (not in alias map, returned as Title Case)
    """
    if not raw_skill:
        return ""

    cleaned = raw_skill.strip()

    # Look up in alias map using lowercase key
    lookup_key = cleaned.lower()
    if lookup_key in SKILL_ALIASES:
        normalized = SKILL_ALIASES[lookup_key]
        if normalized != cleaned:
            logger.debug(f"Skill normalized: '{raw_skill}' → '{normalized}'")
        return normalized

    # Not in alias map — return with Title Case as a fallback
    # This handles skills we don't know about (new frameworks, tools)
    return cleaned.title() if cleaned.isupper() else cleaned
