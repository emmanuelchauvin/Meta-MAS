import uuid
from dataclasses import dataclass, field
from typing import Dict, Any

@dataclass(frozen=True)
class AgentDNA:
    uid: uuid.UUID
    generation: int
    role_prompt: str
    temperature: float
    metadata: Dict[str, Any] = field(default_factory=dict)
