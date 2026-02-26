from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ErrorInfo:
    type: str
    retryable: bool


ERROR_PATTERNS: tuple[tuple[re.Pattern[str], ErrorInfo], ...] = (
    (re.compile(r"(connect|timeout|network|dns|unreachable)", re.IGNORECASE), ErrorInfo("NetworkError", True)),
    (re.compile(r"(authenticate|private\s*key|no wallet|invalid\s*key)", re.IGNORECASE), ErrorInfo("AuthError", False)),
    (re.compile(r"(invalid|must be|expected|parse)", re.IGNORECASE), ErrorInfo("ValidationError", False)),
    (re.compile(r"(rate\s*limit|429|too many)", re.IGNORECASE), ErrorInfo("RateLimitError", True)),
    (re.compile(r"(geoblock|restricted|geo)", re.IGNORECASE), ErrorInfo("GeoblockError", False)),
    (re.compile(r"(insufficient|not enough|balance.*low)", re.IGNORECASE), ErrorInfo("InsufficientFundsError", False)),
)


def classify_error(message: str) -> ErrorInfo:
    for pattern, info in ERROR_PATTERNS:
        if pattern.search(message):
            return info
    return ErrorInfo("UnknownError", False)
