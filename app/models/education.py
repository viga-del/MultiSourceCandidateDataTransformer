from dataclasses import dataclass
from typing import Optional


@dataclass
class Education:
    institution: str
    degree:     Optional[str] = None
    field:      Optional[str] = None
    start_year: Optional[int] = None
    end_year:   Optional[int] = None
