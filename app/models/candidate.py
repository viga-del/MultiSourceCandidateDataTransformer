from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

from app.models.skill       import Skill
from app.models.experience  import Experience
from app.models.education   import Education
from app.models.provenance  import ProvenanceRecord


@dataclass
class CandidateProfile:
    """Central object that flows through the entire pipeline and becomes the final JSON output."""

    candidate_id: str = ""
    full_name:    str = ""
    emails:       List[str] = field(default_factory=list)
    phones:       List[str] = field(default_factory=list)

    location: Dict[str, Any] = field(default_factory=dict)

    links: Dict[str, Any] = field(default_factory=lambda: {
        "linkedin":  None,
        "github":    None,
        "portfolio": None,
        "other":     []
    })

    headline:         Optional[str]   = None
    years_experience: Optional[float] = None

    skills:     List[Skill]      = field(default_factory=list)
    experience: List[Experience] = field(default_factory=list)
    education:  List[Education]  = field(default_factory=list)

    provenance:         List[ProvenanceRecord] = field(default_factory=list)
    confidence:         Dict[str, float]       = field(default_factory=dict)
    overall_confidence: float                  = 0.0

    # Internal — tracks which sources were processed (not included in final output)
    _sources_processed: List[str] = field(default_factory=list)
