from __future__ import annotations

from enum import Enum
from typing import List, Optional

import chess

from game_hub.game import Game, GameState, MoveResult


class ChessMode(str, Enum):
    """Mode A: OpenClaw selects moves. Mode B: Stockfish plays, OpenClaw comments."""

    OPENCLAW = "openclaw"
    STOCKFISH = "stockfish"


class Chess(Game):
    game_type = "chess"

    def __init__(
        self,
        fen: Optional[str] = None,
        move_history: Optional[List[str]] = None,
        human_side: str = "white",
        ai_side: str = "black",
        stockfish_path: str = "stockfish",
        chess_mode: str = ChessMode.OPENCLAW.value,
    ) -> None:
        self.board = chess.Board(fen) if fen else chess.Board()
        self.move_history: List[str] = list(move_history or [])
        self.human_side = human_side
        self.ai_side = ai_side
        self.stockfish_path = stockfish_path
        self.chess_mode = chess_mode

    def state(self) -> GameState:
        side = "white" if self.board.turn == chess.WHITE else "black"
        return GameState(
            game_type=self.game_type,
            board=self.board.fen(),
            side_to_play=side,
            move_history=list(self.move_history),
            metadata={
                "human_side": self.human_side,
                "ai_side": self.ai_side,
                "stockfish_path": self.stockfish_path,
                "chess_mode": self.chess_mode,
            },
        )

    def render(self) -> str:
        side = "white" if self.board.turn == chess.WHITE else "black"
        lines = [f"Side to play: {side}", f"Mode: {self.chess_mode}", "", str(self.board), ""]
        if self.board.is_check():
            lines.append("(check)")
        return "\n".join(lines)

    def strategic_context(self) -> str:
        hints = []
        if self.board.is_check():
            hints.append("You are in check — prioritize king safety.")
        if self.board.is_checkmate():
            hints.append("Checkmate is on the board.")
        hints.append("Consider development, center control, piece activity, and pawn structure.")
        return "\n".join(hints)

    def _parse_move(self, move: str) -> Optional[chess.Move]:
        move = move.strip()
        try:
            parsed = self.board.parse_san(move)
            if parsed in self.board.legal_moves:
                return parsed
        except (chess.InvalidMoveError, chess.IllegalMoveError, chess.AmbiguousMoveError):
            pass
        try:
            parsed = chess.Move.from_uci(move.lower())
            if parsed in self.board.legal_moves:
                return parsed
        except (chess.InvalidMoveError, ValueError):
            pass
        return None

    def validate_move(self, move: str, actor: str) -> MoveResult:
        if self.is_game_over():
            return MoveResult(False, rejection_reason="game_over")
        side = "white" if self.board.turn == chess.WHITE else "black"
        if actor != side:
            return MoveResult(False, rejection_reason=f"not_{side}_turn")
        parsed = self._parse_move(move)
        if not parsed:
            return MoveResult(False, rejection_reason="illegal_move")
        return MoveResult(True, move=move, board_before=self.board.fen())

    def apply_move(self, move: str, actor: str) -> MoveResult:
        validated = self.validate_move(move, actor)
        if not validated.accepted:
            return validated
        parsed = self._parse_move(move)
        assert parsed is not None
        san = self.board.san(parsed)
        self.board.push(parsed)
        self.move_history.append(san)
        return MoveResult(
            True,
            move=san,
            board_before=validated.board_before,
            board_after=self.board.fen(),
        )

    def legal_moves(self) -> List[str]:
        return [self.board.san(m) for m in self.board.legal_moves]

    def is_game_over(self) -> bool:
        return self.board.is_game_over()

    def winner(self) -> Optional[str]:
        if not self.board.is_game_over():
            return None
        outcome = self.board.outcome()
        if outcome is None:
            return "draw"
        if outcome.winner is None:
            return "draw"
        return "white" if outcome.winner == chess.WHITE else "black"

    def stockfish_move(self, depth: int = 10) -> Optional[str]:
        """Mode B only — engine selects the move."""
        try:
            with chess.engine.SimpleEngine.popen_uci(self.stockfish_path) as engine:
                result = engine.play(self.board, chess.engine.Limit(depth=depth))
                if result.move is None:
                    return None
                return self.board.san(result.move)
        except (chess.engine.EngineError, FileNotFoundError, OSError):
            return None

    def serialize(self) -> dict:
        s = self.state()
        return {
            "game_type": s.game_type,
            "board": s.board,
            "side_to_play": s.side_to_play,
            "move_history": s.move_history,
            "metadata": s.metadata,
        }

    @classmethod
    def deserialize(cls, data: dict) -> "Chess":
        meta = data.get("metadata", {})
        return cls(
            fen=data.get("board"),
            move_history=data.get("move_history"),
            human_side=meta.get("human_side", "white"),
            ai_side=meta.get("ai_side", "black"),
            stockfish_path=meta.get("stockfish_path", "stockfish"),
            chess_mode=meta.get("chess_mode", ChessMode.OPENCLAW.value),
        )


ChessEngine = Chess
