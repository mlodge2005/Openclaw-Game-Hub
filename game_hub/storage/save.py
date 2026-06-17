from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from game_hub.game import Game
from game_hub.games.checkers import Checkers
from game_hub.games.chess import Chess, ChessMode
from game_hub.games.tictactoe import TicTacToe

GAME_REGISTRY: dict[str, type[Game]] = {
    "tictactoe": TicTacToe,
    "checkers": Checkers,
    "chess": Chess,
}


def new_game_id() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{ts}-{uuid4().hex[:8]}"


def create_game(game_type: str, **kwargs: Any) -> Game:
    factory = GAME_REGISTRY.get(game_type)
    if not factory:
        raise ValueError(f"unknown game type: {game_type}")
    if game_type == "chess":
        return Chess(
            human_side=kwargs.get("human_side", "white"),
            ai_side=kwargs.get("ai_side", "black"),
            stockfish_path=kwargs.get("stockfish_path", "stockfish"),
            chess_mode=kwargs.get("chess_mode", ChessMode.OPENCLAW.value),
        )
    return factory(
        human_side=kwargs.get("human_side", "X" if game_type == "tictactoe" else "red"),
        ai_side=kwargs.get("ai_side", "O" if game_type == "tictactoe" else "black"),
    )


# Backward-compatible alias
create_engine = create_game


def load_game(data: dict[str, Any]) -> Game:
    game_type = str(data.get("game_type", ""))
    factory = GAME_REGISTRY.get(game_type)
    if not factory:
        raise ValueError(f"unknown game type: {game_type}")
    return factory.deserialize(data)


load_engine = load_game


def save_game(path: Path, *, game_id: str, game: Game, metadata: Optional[dict[str, Any]] = None) -> None:
    payload = {
        "game_id": game_id,
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "state": game.serialize(),
        "metadata": metadata or {},
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def load_saved_game(path: Path) -> tuple[str, Game, dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    game_id = data.get("game_id", "unknown")
    game = load_game(data.get("state", data))
    return game_id, game, data.get("metadata", {})
