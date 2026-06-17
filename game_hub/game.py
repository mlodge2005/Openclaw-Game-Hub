from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, List, Optional


@dataclass
class MoveResult:
    accepted: bool
    move: Optional[str] = None
    rejection_reason: Optional[str] = None
    board_before: Optional[Any] = None
    board_after: Optional[Any] = None

    @property
    def legal(self) -> bool:
        return self.accepted


@dataclass
class GameState:
    game_type: str
    board: Any
    side_to_play: str
    move_history: List[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class Game(ABC):
    """Uniform interface — the hub does not care which game is active."""

    game_type: str

    @abstractmethod
    def state(self) -> GameState:
        ...

    @abstractmethod
    def legal_moves(self) -> List[str]:
        ...

    @abstractmethod
    def validate_move(self, move: str, actor: str) -> MoveResult:
        ...

    @abstractmethod
    def apply_move(self, move: str, actor: str) -> MoveResult:
        ...

    @abstractmethod
    def winner(self) -> Optional[str]:
        ...

    @abstractmethod
    def serialize(self) -> dict[str, Any]:
        ...

    @classmethod
    @abstractmethod
    def deserialize(cls, data: dict[str, Any]) -> "Game":
        ...

    def render(self) -> str:
        """Human-readable board for terminal + OpenClaw prompts."""
        return str(self.state().board)

    def is_game_over(self) -> bool:
        return self.winner() is not None

    def current_actor(self) -> str:
        return self.state().side_to_play

    def strategic_context(self) -> str:
        """Optional hints for OpenClaw — not used for rule enforcement."""
        return ""
