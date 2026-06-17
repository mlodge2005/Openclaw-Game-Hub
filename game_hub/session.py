from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from game_hub.config import HubConfig
from game_hub.game import Game
from game_hub.games.chess import ChessMode
from game_hub.engine.move_gate import MoveGate
from game_hub.logging.game_logger import GameLogger
from game_hub.openclaw.errors import OpenClawUnavailable
from game_hub.openclaw.opponent import OpenClawOpponent
from game_hub.storage.save import save_game


class OpponentMode(str, Enum):
    OPENCLAW = "openclaw"
    HUMAN = "human"


@dataclass
class GameSession:
    game_id: str
    game: Game
    human_side: str
    ai_side: str
    opponent_mode: OpponentMode
    config: HubConfig
    logger: GameLogger
    chess_mode: str = ChessMode.OPENCLAW.value
    gate: Optional[MoveGate] = None
    openclaw: Optional[OpenClawOpponent] = None

    def __post_init__(self) -> None:
        self.logger.start_game(self.game_id)
        self.gate = MoveGate(self.game, self.game_id, on_turn=self.logger.log_turn)
        if self.opponent_mode == OpponentMode.OPENCLAW:
            self.openclaw = OpenClawOpponent(self.config)

    def header(self) -> str:
        state = self.game.state()
        chess_note = f" | chess mode: {self.chess_mode}" if state.game_type == "chess" else ""
        return (
            f"\n=== Game Hub | {state.game_type} | ID: {self.game_id} ===\n"
            f"You: {self.human_side} | OpenClaw: {self.ai_side} ({self.opponent_mode.value}){chess_note}\n"
        )

    def run_interactive(self) -> None:
        print(self.header())
        while not self.game.is_game_over():
            print(self.game.render())
            actor = self.game.current_actor()

            if actor == self.human_side:
                move = self._prompt_human_move()
                if move is None:
                    continue
                result = self.gate.propose_move(move, actor)  # type: ignore[union-attr]
                if not result.accepted:
                    print(f"Illegal move: {result.rejection_reason}")
                    continue
            else:
                move, commentary = self._get_opponent_move()
                if move is None:
                    continue
                if commentary:
                    print(f"OpenClaw: {commentary}")
                print(f"Opponent plays: {move}")
                time.sleep(0.2)
                result = self.gate.propose_move(move, actor, commentary=commentary)  # type: ignore[union-attr]
                if not result.accepted:
                    print(f"Move rejected by Move Gate: {result.rejection_reason}")

        print(self.game.render())
        print(f"\nGame over. Result: {self.game.winner() or 'unknown'}")
        path = self._autosave()
        print(f"Saved to {path}")

    def _prompt_human_move(self) -> Optional[str]:
        legal = self.game.legal_moves()
        print(f"Legal moves: {', '.join(legal[:40])}{'...' if len(legal) > 40 else ''}")
        raw = input("Your move (legal | save | quit): ").strip()
        if not raw:
            return None
        lower = raw.lower()
        if lower == "quit":
            path = self._autosave()
            print(f"Saved to {path}")
            raise SystemExit(0)
        if lower == "save":
            path = self._autosave()
            print(f"Saved to {path}")
            return None
        if lower == "legal":
            for m in legal:
                print(m)
            return None
        return raw

    def _get_opponent_move(self) -> tuple[Optional[str], Optional[str]]:
        if self.opponent_mode == OpponentMode.HUMAN:
            raw = input(f"Player {self.game.current_actor()} move: ").strip()
            return raw or None, None

        if self.game.game_type == "chess" and self.chess_mode == ChessMode.STOCKFISH.value:
            return self._chess_stockfish_turn()

        return self._openclaw_turn()

    def _openclaw_turn(self) -> tuple[Optional[str], Optional[str]]:
        assert self.openclaw is not None
        while True:
            try:
                return self.openclaw.request_move_sync(self.game)
            except OpenClawUnavailable as exc:
                print(f"\nOpenClaw unavailable: {exc}")
                choice = input("Retry (r), save and exit (s), quit without save (q): ").strip().lower()
                if choice == "r":
                    continue
                if choice == "s":
                    path = self._autosave()
                    print(f"Saved to {path}")
                    raise SystemExit(0)
                raise SystemExit(1)

    def _chess_stockfish_turn(self) -> tuple[Optional[str], Optional[str]]:
        from game_hub.games.chess import Chess

        assert isinstance(self.game, Chess)
        move = self.game.stockfish_move()
        if not move:
            print(f"Stockfish unavailable (path: {self.game.stockfish_path})")
            choice = input("Retry (r), save and exit (s), quit (q): ").strip().lower()
            if choice == "r":
                return self._chess_stockfish_turn()
            if choice == "s":
                path = self._autosave()
                print(f"Saved to {path}")
                raise SystemExit(0)
            raise SystemExit(1)

        commentary = None
        if self.openclaw:
            try:
                commentary = self.openclaw.request_commentary_sync(self.game, move, self.ai_side)
            except OpenClawUnavailable:
                commentary = "(OpenClaw commentary unavailable)"
        return move, commentary

    def _autosave(self) -> str:
        saves_dir = self.config.data_dir / "saves"
        path = saves_dir / f"{self.game_id}.json"
        meta = {
            "human_side": self.human_side,
            "ai_side": self.ai_side,
            "opponent_mode": self.opponent_mode.value,
            "chess_mode": self.chess_mode,
        }
        if self.game.game_type == "chess":
            meta["stockfish_path"] = self.game.state().metadata.get("stockfish_path", "stockfish")
        save_game(path, game_id=self.game_id, game=self.game, metadata=meta)
        self.logger.export_game(
            self.game_id,
            {"game_id": self.game_id, "state": self.game.serialize(), "metadata": meta},
        )
        return str(path)
