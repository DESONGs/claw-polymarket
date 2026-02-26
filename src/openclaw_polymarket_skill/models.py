from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable


class ActionCategory(str, Enum):
    READ = "read"
    READ_AUTH = "read_auth"
    WRITE = "write"


@dataclass(frozen=True)
class ActionSpec:
    name: str
    category: ActionCategory
    required_params: tuple[str, ...]
    builder: Callable[[dict[str, Any]], list[str]]

    @property
    def is_write(self) -> bool:
        return self.category == ActionCategory.WRITE
