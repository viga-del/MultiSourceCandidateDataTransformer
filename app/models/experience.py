from dataclasses import dataclass
from typing import Optional


@dataclass
class Experience:
    company: str
    title:   Optional[str] = None
    start:   Optional[str] = None  # YYYY-MM format
    end:     Optional[str] = None  # YYYY-MM or "Present"
    summary: Optional[str] = None
