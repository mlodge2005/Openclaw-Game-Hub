"""Terminal board rendering helpers."""

from __future__ import annotations

import os
import sys
from typing import List, Optional, Sequence


def use_unicode_pieces() -> bool:
    """Return False when GAME_HUB_ASCII_PIECES=1 forces ASCII piece symbols."""
    return os.environ.get("GAME_HUB_ASCII_PIECES", "").strip().lower() not in (
        "1",
        "true",
        "yes",
    )


def _stdout_supports_unicode() -> bool:
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    try:
        for ch in "●○♔♚":
            ch.encode(encoding)
        return True
    except (UnicodeEncodeError, LookupError):
        return False


def checkers_piece_char(piece: str, unicode_mode: Optional[bool] = None) -> str:
    if unicode_mode is None:
        unicode_mode = use_unicode_pieces() and _stdout_supports_unicode()
    if not unicode_mode:
        return piece if piece != "." else "."
    mapping = {
        ".": ".",
        "r": "●",
        "R": "♔",
        "b": "○",
        "B": "♚",
    }
    return mapping.get(piece, piece)


def internal_rank(internal_row: int) -> int:
    """Map internal row index (0=top) to chess rank 1-8 (1=bottom)."""
    return 8 - internal_row


def internal_row_from_rank(rank: int) -> int:
    return 8 - rank


def render_checkers_board(
    board: Sequence[Sequence[str]],
    *,
    human_side: str = "red",
    unicode_pieces: Optional[bool] = None,
) -> str:
    """
    Render 8x8 checkers with a-h / 1-8 coordinates matching move notation.
    Human player's pieces appear at the bottom of the terminal.
    """
    flip = human_side == "black"
    if unicode_pieces is None:
        unicode_pieces = use_unicode_pieces() and _stdout_supports_unicode()

    file_labels = list("abcdefgh") if not flip else list("hgfedcba")
    border = "  +-----------------+"
    lines: List[str] = ["    " + " ".join(file_labels), border]

    for display_idx in range(8):
        internal_row = display_idx if not flip else 7 - display_idx
        rank = internal_rank(internal_row)
        col_order = range(8) if not flip else range(7, -1, -1)
        cells = [
            checkers_piece_char(board[internal_row][col], unicode_pieces)
            for col in col_order
        ]
        lines.append(f"{rank} | {' '.join(cells)} |")

    lines.append(border)
    return "\n".join(lines)
