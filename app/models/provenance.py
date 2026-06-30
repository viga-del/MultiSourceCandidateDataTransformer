from dataclasses import dataclass
from typing import Optional


@dataclass
class ProvenanceRecord:
    field:  str
    source: str
    method: str
    value:  Optional[str] = None
