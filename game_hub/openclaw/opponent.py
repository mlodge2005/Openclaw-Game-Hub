from __future__ import annotations

import asyncio
from typing import Optional

from game_hub.config import HubConfig
from game_hub.game import Game
from game_hub.openclaw.client import OpenClawClient, OpenClawError
from game_hub.openclaw.device import load_or_create_device_identity
from game_hub.openclaw.errors import OpenClawUnavailable
from game_hub.openclaw.prompts import build_move_prompt, parse_move_response


class OpenClawOpponent:
    def __init__(self, config: HubConfig) -> None:
        self.config = config
        self.device_path = config.data_dir / "device.json"
        self._client: Optional[OpenClawClient] = None
        self._connected = False

    def _get_client(self) -> OpenClawClient:
        if self._client is None:
            identity = load_or_create_device_identity(self.device_path)
            self._client = OpenClawClient(
                url=self.config.openclaw.url,
                token=self.config.openclaw.token,
                device_identity=identity,
                device_path=self.device_path,
                tls_fingerprint=self.config.openclaw.tls_fingerprint,
            )
        return self._client

    async def connect(self) -> None:
        await self._get_client().connect()
        self._connected = True

    async def close(self) -> None:
        if self._client:
            await self._client.close()
            self._client = None
        self._connected = False

    async def request_move(
        self,
        game: Game,
        *,
        max_retries: int = 3,
    ) -> tuple[str, Optional[str]]:
        if not self._connected:
            await self.connect()

        state = game.state()
        legal = game.legal_moves()
        last_error: Optional[str] = None

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
                response = await self._get_client().request_move(
                    message=prompt,
                    session_key=self.config.openclaw.session_key,
                    agent_id=self.config.openclaw.agent_id,
                    timeout_seconds=self.config.openclaw.timeout_seconds,
                )
            except OpenClawError as exc:
                raise OpenClawUnavailable(str(exc)) from exc

            move, commentary = parse_move_response(response.text, legal)
            if move:
                return move, commentary
            last_error = "response did not contain a legal move"

        raise OpenClawUnavailable(last_error or "no valid move after retries")

    async def request_commentary(self, game: Game, move: str, side: str) -> Optional[str]:
        if not self._connected:
            await self.connect()
        prompt = (
            f"Terminal Game Hub chess analysis (Mode B).\n"
            f"Move played by {side}: {move}\n\n"
            f"{game.render()}\n\n"
            'Respond JSON only: {"commentary": "one sentence of analysis"}'
        )
        try:
            response = await self._get_client().request_move(
                message=prompt,
                session_key=self.config.openclaw.session_key,
                agent_id=self.config.openclaw.agent_id,
                timeout_seconds=60,
            )
            _, commentary = parse_move_response(response.text, [])
            return commentary or response.text[:300]
        except OpenClawError:
            return None

    def request_move_sync(self, game: Game, **kwargs) -> tuple[str, Optional[str]]:
        return asyncio.run(self._with_session(self.request_move(game, **kwargs)))

    def request_commentary_sync(self, game: Game, move: str, side: str) -> Optional[str]:
        return asyncio.run(self._with_session(self.request_commentary(game, move, side)))

    async def _with_session(self, coro):
        await self.connect()
        try:
            return await coro
        finally:
            await self.close()
