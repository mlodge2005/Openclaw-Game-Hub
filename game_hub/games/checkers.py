from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from game_hub.display.board import internal_rank, internal_row_from_rank, render_checkers_board
from game_hub.game import Game, GameState, MoveResult


def _initial_board() -> List[List[str]]:
    board = [["." for _ in range(8)] for _ in range(8)]
    for row in range(3):
        for col in range(8):
            if (row + col) % 2 == 1:
                board[row][col] = "b"
    for row in range(5, 8):
        for col in range(8):
            if (row + col) % 2 == 1:
                board[row][col] = "r"
    return board


def _piece_side(piece: str) -> Optional[str]:
    if piece in ("b", "B"):
        return "black"
    if piece in ("r", "R"):
        return "red"
    return None


def _is_king(piece: str) -> bool:
    return piece in ("B", "R")


class Checkers(Game):
    game_type = "checkers"

    def __init__(
        self,
        board: Optional[List[List[str]]] = None,
        side_to_play: str = "red",
        move_history: Optional[List[str]] = None,
        human_side: str = "red",
        ai_side: str = "black",
    ) -> None:
        self.board = [row[:] for row in (board or _initial_board())]
        self.side_to_play = side_to_play
        self.move_history: List[str] = list(move_history or [])
        self.human_side = human_side
        self.ai_side = ai_side

    def state(self) -> GameState:
        return GameState(
            game_type=self.game_type,
            board=[row[:] for row in self.board],
            side_to_play=self.side_to_play,
            move_history=list(self.move_history),
            metadata={"human_side": self.human_side, "ai_side": self.ai_side},
        )

    def render(self) -> str:
        """Board for terminal + OpenClaw prompts (matches move notation)."""
        return render_checkers_board(self.board, human_side=self.human_side)

    def strategic_context(self) -> str:
        jumps = [m for m in self.legal_moves() if "x" in m]
        if jumps:
            return "Captures are available — forced jumps may apply in this ruleset."
        return "Control the center, advance pieces toward promotion, avoid leaving blots."

    def _parse_square(self, token: str) -> Optional[Tuple[int, int]]:
        token = token.strip().lower()
        if len(token) != 2:
            return None
        col = ord(token[0]) - ord("a")
        try:
            rank = int(token[1])
        except ValueError:
            return None
        if not (0 <= col <= 7 and 1 <= rank <= 8):
            return None
        row = internal_row_from_rank(rank)
        return row, col

    def _format_square(self, row: int, col: int) -> str:
        return f"{chr(ord('a') + col)}{internal_rank(row)}"

    def _in_bounds(self, row: int, col: int) -> bool:
        return 0 <= row <= 7 and 0 <= col <= 7

    def _directions(self, piece: str) -> List[Tuple[int, int]]:
        if _is_king(piece):
            return [(-1, -1), (-1, 1), (1, -1), (1, 1)]
        if piece == "r":
            return [(-1, -1), (-1, 1)]
        return [(1, -1), (1, 1)]

    def _generate_moves_for_piece(self, row: int, col: int) -> List[Dict]:
        piece = self.board[row][col]
        side = _piece_side(piece)
        if not side:
            return []
        moves: List[Dict] = []
        jumps: List[Dict] = []

        for dr, dc in self._directions(piece):
            nr, nc = row + dr, col + dc
            if self._in_bounds(nr, nc) and self.board[nr][nc] == ".":
                moves.append({"from": (row, col), "to": (nr, nc), "captures": []})
            jr, jc = row + 2 * dr, col + 2 * dc
            mr, mc = row + dr, col + dc
            if self._in_bounds(jr, jc) and self.board[jr][jc] == ".":
                mid = self.board[mr][mc]
                if mid != "." and _piece_side(mid) != side:
                    jumps.append({"from": (row, col), "to": (jr, jc), "captures": [(mr, mc)]})

        return jumps if jumps else moves

    def _all_moves(self, side: str) -> List[Dict]:
        result: List[Dict] = []
        for row in range(8):
            for col in range(8):
                piece = self.board[row][col]
                if _piece_side(piece) == side:
                    result.extend(self._generate_moves_for_piece(row, col))
        return result

    def _move_to_notation(self, move: Dict) -> str:
        fr, fc = move["from"]
        tr, tc = move["to"]
        sep = "x" if move["captures"] else "-"
        return f"{self._format_square(fr, fc)}{sep}{self._format_square(tr, tc)}"

    def _parse_move(self, move: str) -> Optional[Dict]:
        move = move.strip().lower().replace(" ", "")
        sep = "x" if "x" in move else "-" if "-" in move else None
        if not sep:
            return None
        a, b = move.split(sep, 1)
        start = self._parse_square(a)
        end = self._parse_square(b)
        if not start or not end:
            return None
        side = self.side_to_play
        for candidate in self._all_moves(side):
            if candidate["from"] == start and candidate["to"] == end:
                return candidate
        return None

    def validate_move(self, move: str, actor: str) -> MoveResult:
        if self.is_game_over():
            return MoveResult(False, rejection_reason="game_over")
        if actor != self.side_to_play:
            return MoveResult(False, rejection_reason=f"not_{self.side_to_play}_turn")
        parsed = self._parse_move(move)
        if not parsed:
            return MoveResult(False, rejection_reason="illegal_move")
        return MoveResult(True, move=move, board_before=[r[:] for r in self.board])

    def apply_move(self, move: str, actor: str) -> MoveResult:
        validated = self.validate_move(move, actor)
        if not validated.accepted:
            return validated
        parsed = self._parse_move(move)
        assert parsed is not None
        fr, fc = parsed["from"]
        tr, tc = parsed["to"]
        piece = self.board[fr][fc]
        self.board[fr][fc] = "."
        for cr, cc in parsed["captures"]:
            self.board[cr][cc] = "."
        if piece == "r" and tr == 0:
            piece = "R"
        elif piece == "b" and tr == 7:
            piece = "B"
        self.board[tr][tc] = piece
        self.move_history.append(move)
        self.side_to_play = "black" if self.side_to_play == "red" else "red"
        return MoveResult(
            True,
            move=move,
            board_before=validated.board_before,
            board_after=[r[:] for r in self.board],
        )

    def legal_moves(self) -> List[str]:
        return [self._move_to_notation(m) for m in self._all_moves(self.side_to_play)]

    def _count_pieces(self, side: str) -> int:
        target = "rR" if side == "red" else "bB"
        return sum(1 for row in self.board for cell in row if cell in target)

    def is_game_over(self) -> bool:
        return self.winner() is not None

    def winner(self) -> Optional[str]:
        if self._count_pieces("red") == 0:
            return "black"
        if self._count_pieces("black") == 0:
            return "red"
        if not self._all_moves(self.side_to_play):
            return "black" if self.side_to_play == "red" else "red"
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
    def deserialize(cls, data: dict) -> "Checkers":
        meta = data.get("metadata", {})
        return cls(
            board=data.get("board"),
            side_to_play=data.get("side_to_play", "red"),
            move_history=data.get("move_history"),
            human_side=meta.get("human_side", "red"),
            ai_side=meta.get("ai_side", "black"),
        )


CheckersEngine = Checkers
