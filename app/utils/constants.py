# Source name labels used in provenance and confidence
SOURCE_RESUME    = "Resume"
SOURCE_CSV       = "CSV"
SOURCE_JSON      = "JSON"
SOURCE_GITHUB    = "GitHub"
SOURCE_LINKEDIN  = "LinkedIn"
SOURCE_NOTES     = "Notes"

# Supported file extensions
EXT_PDF   = ".pdf"
EXT_DOCX  = ".docx"
EXT_CSV   = ".csv"
EXT_JSON  = ".json"
EXT_TXT   = ".txt"
EXT_XLSX  = ".xlsx"

# Canonical field name constants
FIELD_FULL_NAME        = "full_name"
FIELD_EMAILS           = "emails"
FIELD_PHONES           = "phones"
FIELD_LOCATION         = "location"
FIELD_LINKS            = "links"
FIELD_HEADLINE         = "headline"
FIELD_YEARS_EXPERIENCE = "years_experience"
FIELD_SKILLS           = "skills"
FIELD_EXPERIENCE       = "experience"
FIELD_EDUCATION        = "education"
FIELD_PROVENANCE       = "provenance"
FIELD_OVERALL_CONF     = "overall_confidence"

# Base confidence scores per source (also in confidence_rules.json)
CONFIDENCE_RESUME   = 0.95
CONFIDENCE_CSV      = 0.90
CONFIDENCE_JSON     = 0.90
CONFIDENCE_LINKEDIN = 0.85
CONFIDENCE_GITHUB   = 0.75
CONFIDENCE_NOTES    = 0.70

# Conflict resolution priority — lower number wins
PRIORITY_ORDER = {
    SOURCE_RESUME:   1,
    SOURCE_CSV:      2,
    SOURCE_JSON:     2,
    SOURCE_LINKEDIN: 3,
    SOURCE_GITHUB:   4,
    SOURCE_NOTES:    5,
}
