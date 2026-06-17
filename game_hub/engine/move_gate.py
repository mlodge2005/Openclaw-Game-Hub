from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, List, Optional

from game_hub.game import Game, MoveResult


@dataclass
class TurnRecord:
    game_id: str
    game_type: str
    turn_number: int
    actor: str
    board_state_before: object
    legal_moves: List[str]
    selected_move: str
    accepted: bool
    rejection_reason: Optional[str]
    board_state_after: Optional[object]
    timestamp: str
    commentary: Optional[str] = None

    # Backward-compatible aliases for older log readers
    @property
    def move(self) -> str:
        return self.selected_move

    @property
    def legal(self) -> bool:
        return self.accepted


class MoveGate:
    """Validate locally, then apply. OpenClaw proposes; the gate enforces reality."""

    def __init__(
        self,
        game: Game,
        game_id: str,
        on_turn: Optional[Callable[[TurnRecord], None]] = None,
    ) -> None:
        self.game = game
        self.game_id = game_id
        self.turn_number = len(game.state().move_history)
        self.on_turn = on_turn

    def propose_move(
        self,
        move: str,
        actor: str,
        *,
        commentary: Optional[str] = None,
    ) -> MoveResult:
        move = move.strip()
        before = self.game.state().board
        legal_at_turn = self.game.legal_moves()
        result = self.game.validate_move(move, actor)

        record = TurnRecord(
            game_id=self.game_id,
            game_type=self.game.game_type,
            turn_number=self.turn_number,
            actor=actor,
            board_state_before=before,
            legal_moves=list(legal_at_turn),
            selected_move=move,
            accepted=result.accepted,
            rejection_reason=result.rejection_reason,
            board_state_after=None,
            timestamp=datetime.now(timezone.utc).isoformat(),
            commentary=commentary,
        )

        if not result.accepted:
            if self.on_turn:
                self.on_turn(record)
            return result

        applied = self.game.apply_move(move, actor)
        record.accepted = applied.accepted
        record.board_state_after = applied.board_after
        if not applied.accepted:
            record.rejection_reason = applied.rejection_reason or "apply_failed"

        self.turn_number += 1
        if self.on_turn:
            self.on_turn(record)
        return applied
