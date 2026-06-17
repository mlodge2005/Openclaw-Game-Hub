from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List

from game_hub.engine.move_gate import TurnRecord


class GameLogger:
    def __init__(self, log_dir: Path) -> None:
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._records: List[TurnRecord] = []
        self._game_id: str = ""

    def start_game(self, game_id: str) -> None:
        self._game_id = game_id
        self._records = []

    def log_turn(self, record: TurnRecord) -> None:
        self._records.append(record)
        path = self.log_dir / f"{record.game_id}.jsonl"
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(asdict(record), default=str) + "\n")

    def export_game(self, game_id: str, payload: dict[str, Any]) -> Path:
        path = self.log_dir / f"{game_id}_complete.json"
        payload["exported_at"] = datetime.now(timezone.utc).isoformat()
        path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        return path
