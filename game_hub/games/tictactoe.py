from __future__ import annotations

from typing import List, Optional

from game_hub.game import Game, GameState, MoveResult

WIN_LINES = (
    (0, 1, 2), (3, 4, 5), (6, 7, 8),
    (0, 3, 6), (1, 4, 7), (2, 5, 8),
    (0, 4, 8), (2, 4, 6),
)


class TicTacToe(Game):
    game_type = "tictactoe"

    def __init__(
        self,
        board: Optional[List[str]] = None,
        side_to_play: str = "X",
        move_history: Optional[List[str]] = None,
        human_side: str = "X",
        ai_side: str = "O",
    ) -> None:
        self.board: List[str] = list(board) if board else [""] * 9
        self.side_to_play = side_to_play
        self.move_history: List[str] = list(move_history or [])
        self.human_side = human_side
        self.ai_side = ai_side

    def state(self) -> GameState:
        return GameState(
            game_type=self.game_type,
            board=list(self.board),
            side_to_play=self.side_to_play,
            move_history=list(self.move_history),
            metadata={"human_side": self.human_side, "ai_side": self.ai_side},
        )

    def render(self) -> str:
        def cell(i: int) -> str:
            return self.board[i] or str(i + 1)

        rows = [
            f" {cell(0)} | {cell(1)} | {cell(2)} ",
            "---+---+---",
            f" {cell(3)} | {cell(4)} | {cell(5)} ",
            "---+---+---",
            f" {cell(6)} | {cell(7)} | {cell(8)} ",
        ]
        return f"Side to play: {self.side_to_play}\n" + "\n".join(rows)

    def strategic_context(self) -> str:
        lines = []
        if self._winning_move_exists(self.side_to_play):
            lines.append("You have an immediate winning move available.")
        opp = "O" if self.side_to_play == "X" else "X"
        if self._winning_move_exists(opp):
            lines.append("Opponent threatens a win on the next turn — block if possible.")
        if not self.board[4]:
            lines.append("Center (5) is often strong if available.")
        return "\n".join(lines)

    def _winning_move_exists(self, player: str) -> bool:
        for a, b, c in WIN_LINES:
            cells = [self.board[a], self.board[b], self.board[c]]
            if cells.count(player) == 2 and "" in cells:
                return True
        return False

    def _parse_move(self, move: str) -> Optional[int]:
        move = move.strip().upper()
        if move in {"A1", "A2", "A3", "B1", "B2", "B3", "C1", "C2", "C3"}:
            mapping = {
                "A1": 0, "A2": 1, "A3": 2,
                "B1": 3, "B2": 4, "B3": 5,
                "C1": 6, "C2": 7, "C3": 8,
            }
            return mapping[move]
        if move.isdigit():
            idx = int(move) - 1
            if 0 <= idx <= 8:
                return idx
        return None

    def validate_move(self, move: str, actor: str) -> MoveResult:
        if self.is_game_over():
            return MoveResult(False, rejection_reason="game_over")
        if actor != self.side_to_play:
            return MoveResult(False, rejection_reason=f"not_{self.side_to_play}_turn")
        idx = self._parse_move(move)
        if idx is None:
            return MoveResult(False, rejection_reason="invalid_format")
        if self.board[idx]:
            return MoveResult(False, rejection_reason="cell_occupied")
        return MoveResult(True, move=move, board_before=list(self.board))

    def apply_move(self, move: str, actor: str) -> MoveResult:
        validated = self.validate_move(move, actor)
        if not validated.accepted:
            return validated
        idx = self._parse_move(move)
        assert idx is not None
        self.board[idx] = actor
        self.move_history.append(move)
        self.side_to_play = "O" if actor == "X" else "X"
        return MoveResult(True, move=move, board_before=validated.board_before, board_after=list(self.board))

    def legal_moves(self) -> List[str]:
        return [str(i + 1) for i, c in enumerate(self.board) if not c]

    def is_game_over(self) -> bool:
        w = self.winner()
        return w is not None

    def winner(self) -> Optional[str]:
        for a, b, c in WIN_LINES:
            if self.board[a] and self.board[a] == self.board[b] == self.board[c]:
                return self.board[a]
        if all(self.board):
            return "draw"
        return None

    def current_actor(self) -> str:
        return self.side_to_play

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
    def deserialize(cls, data: dict) -> "TicTacToe":
        meta = data.get("metadata", {})
        return cls(
            board=data.get("board"),
            side_to_play=data.get("side_to_play", "X"),
            move_history=data.get("move_history"),
            human_side=meta.get("human_side", "X"),
            ai_side=meta.get("ai_side", "O"),
        )


# Backward compatibility
TicTacToeEngine = TicTacToe
