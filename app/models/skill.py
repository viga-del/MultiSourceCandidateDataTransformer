from dataclasses import dataclass, field
from typing import List


@dataclass
class Skill:
    name: str
    confidence: float = 0.0
    # default_factory=list gives each instance its own list (avoids shared mutable default)
    sources: List[str] = field(default_factory=list)
