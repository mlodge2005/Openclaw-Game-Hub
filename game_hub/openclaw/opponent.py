"""OpenClaw opponent — sync HTTP client wrapper."""

from __future__ import annotations

from typing import Optional

from game_hub.config import HubConfig
from game_hub.game import Game
from game_hub.openclaw.client import OpenClawClient, OpenClawError, OpenClawUnavailable
from game_hub.openclaw.prompts import build_move_prompt, parse_move_response


class OpenClawOpponent:
    """Sync opponent calling OpenClaw via HTTP."""

    def __init__(self, config: HubConfig) -> None:
        self.config = config
        self._client = OpenClawClient(
            base_url=config.openclaw.base_url,
            token=config.openclaw.token,
            agent_id=config.openclaw.agent_id,
            timeout_seconds=config.openclaw.timeout_seconds,
        )

    def request_move(self, game: Game, *, max_retries: int = 3) -> tuple[Optional[str], Optional[str]]:
        state = game.state()
        legal = game.legal_moves()
        last_error = None
        for attempt in range(1, max_retries + 1):
            prompt = build_move_prompt(
                game_type=state.game_type,
                board_render=game.render(),
                side_to_play=state.side_to_play,
                legal_moves=legal,
                move_history=state.move_history,
                strategic_context=game.strategic_context(),
                attempt=attempt,
                last_error=last_error,
            )
            try:
                response_text = self._client.request_move(message=prompt)
            except OpenClawError as exc:
                raise OpenClawUnavailable(str(exc)) from exc
            move, commentary = parse_move_response(response_text, legal)
            if move:
                return move, commentary
            last_error = "response did not contain a legal move"
        raise OpenClawUnavailable(last_error or "no valid move after retries")

    def request_commentary(self, game: Game, move: str, side: str) -> Optional[str]:
        prompt = (
            f"Terminal Game Hub chess analysis (Mode B).\n"
            f"Move played by {side}: {move}\n\n{game.render()}\n\n"
            'Respond JSON only: {"commentary": "one sentence of analysis"}'
        )
        try:
            response_text = self._client.request_move(message=prompt, timeout_seconds=60)
            _, commentary = parse_move_response(response_text, [])
            return commentary or response_text[:300]
        except OpenClawError:
            return None
