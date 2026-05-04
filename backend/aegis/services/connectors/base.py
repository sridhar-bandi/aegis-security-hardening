"""Base connector ABC and shared result types."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ConnectorResult:
    success: bool
    output: str = ""
    error: str = ""
    raw: Any = None
    saved_state: dict = field(default_factory=dict)


class BaseConnector(ABC):
    """Abstract base for all target connectors."""

    @abstractmethod
    def connect(self) -> None: ...

    @abstractmethod
    def disconnect(self) -> None: ...

    @abstractmethod
    def run_command(self, command: str) -> ConnectorResult: ...

    def __enter__(self) -> "BaseConnector":
        self.connect()
        return self

    def __exit__(self, *args) -> None:
        self.disconnect()
