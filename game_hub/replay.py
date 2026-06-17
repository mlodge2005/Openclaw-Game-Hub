from __future__ import annotations

import time
from pathlib import Path

from game_hub.engine.move_gate import MoveGate
from game_hub.storage.save import create_game, load_saved_game


def replay_game(save_path: Path, *, delay: float = 0.8) -> None:
    game_id, game, metadata = load_saved_game(save_path)
    history = game.state().move_history

    print(f"\n=== Replay: {game_id} ({game.game_type}) ===\n")
    print(game.render())

    fresh = create_game(
        game.game_type,
        human_side=metadata.get("human_side", _default_human(game.game_type)),
        ai_side=metadata.get("ai_side", _default_ai(game.game_type)),
        stockfish_path=metadata.get("stockfish_path", "stockfish"),
        chess_mode=metadata.get("chess_mode", "openclaw"),
    )
    gate = MoveGate(fresh, game_id)
    sides = _alternating_sides(game.game_type, metadata)

    for i, move in enumerate(history):
        actor = sides[i % 2]
        print(f"\n--- Turn {i + 1}: {actor} plays {move} ---")
        gate.propose_move(move, actor)
        print(fresh.render())
        time.sleep(delay)

    print(f"\nFinal result: {fresh.winner()}")


def _default_human(game_type: str) -> str:
    return {"tictactoe": "X", "checkers": "red", "chess": "white"}.get(game_type, "human")


def _default_ai(game_type: str) -> str:
    return {"tictactoe": "O", "checkers": "black", "chess": "black"}.get(game_type, "ai")


def _alternating_sides(game_type: str, metadata: dict) -> list[str]:
    if game_type == "tictactoe":
        return [metadata.get("human_side", "X"), metadata.get("ai_side", "O")]
    if game_type == "checkers":
        return [metadata.get("human_side", "red"), metadata.get("ai_side", "black")]
    if game_type == "chess":
        return [metadata.get("human_side", "white"), metadata.get("ai_side", "black")]
    return ["human", "ai"]
