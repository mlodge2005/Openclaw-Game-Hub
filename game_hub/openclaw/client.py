from __future__ import annotations

import asyncio
import json
import platform
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Optional
from urllib.parse import urlparse

import websockets
from websockets.asyncio.client import ClientConnection

from game_hub.openclaw.device import (
    DeviceIdentity,
    build_device_auth_payload_v3,
    load_device_token,
    save_device_token,
    sign_device_payload,
)

PROTOCOL_VERSION = 4
DEFAULT_SCOPES = ["operator.read", "operator.write"]
CLIENT_ID = "game-hub"
CLIENT_MODE = "backend"
CLIENT_VERSION = "1.0.0"
ROLE = "operator"


@dataclass
class AgentResponse:
    text: str
    commentary: Optional[str] = None
    raw: Optional[dict[str, Any]] = None


class OpenClawError(Exception):
    pass


@dataclass
class _ActiveRun:
    run_id: str
    chunks: list[str] = field(default_factory=list)
    done: asyncio.Event = field(default_factory=asyncio.Event)
    error: Optional[str] = None


class OpenClawClient:
    """WebSocket client for the OpenClaw Gateway agent RPC."""

    def __init__(
        self,
        url: str,
        token: str,
        device_identity: DeviceIdentity,
        device_path: Optional[Any] = None,
        tls_fingerprint: Optional[str] = None,
    ) -> None:
        self.url = url
        self.token = token
        self.device = device_identity
        self.device_path = device_path
        self.tls_fingerprint = tls_fingerprint
        self._ws: Optional[ClientConnection] = None
        self._pending: dict[str, asyncio.Future[Any]] = {}
        self._challenge: Optional[asyncio.Future[str]] = None
        self._device_token: Optional[str] = None
        self._active_runs: dict[str, _ActiveRun] = {}
        self._reader_task: Optional[asyncio.Task[None]] = None
        if device_path is not None:
            self._device_token = load_device_token(device_path)

    async def connect(self, timeout: float = 30.0) -> dict[str, Any]:
        parsed = urlparse(self.url)
        if parsed.scheme not in ("ws", "wss"):
            raise OpenClawError(f"unsupported URL scheme: {parsed.scheme}")

        self._challenge = asyncio.get_running_loop().create_future()
        self._ws = await asyncio.wait_for(
            websockets.connect(self.url, max_size=25 * 1024 * 1024),
            timeout=timeout,
        )
        self._reader_task = asyncio.create_task(self._reader())

        nonce = await asyncio.wait_for(self._challenge, timeout=timeout)
        hello = await self._request("connect", self._build_connect_params(nonce), timeout=timeout)

        auth = hello.get("auth") if isinstance(hello, dict) else None
        if isinstance(auth, dict):
            device_token = auth.get("deviceToken")
            if device_token and self.device_path is not None:
                save_device_token(self.device_path, str(device_token))
                self._device_token = str(device_token)
        return hello if isinstance(hello, dict) else {}

    def _build_connect_params(self, nonce: str) -> dict[str, Any]:
        signed_at_ms = int(time.time() * 1000)
        scopes = list(DEFAULT_SCOPES)
        auth_token = self.token or self._device_token or ""

        payload = build_device_auth_payload_v3(
            device_id=self.device.device_id,
            client_id=CLIENT_ID,
            client_mode=CLIENT_MODE,
            role=ROLE,
            scopes=scopes,
            signed_at_ms=signed_at_ms,
            token=auth_token,
            nonce=nonce,
            platform_name=platform.system().lower(),
            device_family="raspberry-pi",
        )
        signature = sign_device_payload(self.device.private_key_pem, payload)

        connect_auth: dict[str, str] = {}
        if self.token:
            connect_auth["token"] = self.token
        if self._device_token:
            connect_auth["deviceToken"] = self._device_token

        return {
            "minProtocol": PROTOCOL_VERSION,
            "maxProtocol": PROTOCOL_VERSION,
            "client": {
                "id": CLIENT_ID,
                "version": CLIENT_VERSION,
                "platform": platform.system().lower(),
                "deviceFamily": "raspberry-pi",
                "mode": CLIENT_MODE,
            },
            "role": ROLE,
            "scopes": scopes,
            "caps": [],
            "commands": [],
            "permissions": {},
            "auth": connect_auth or None,
            "locale": "en-US",
            "userAgent": f"terminal-game-hub/{CLIENT_VERSION}",
            "device": {
                "id": self.device.device_id,
                "publicKey": self.device.public_key_raw_b64url,
                "signature": signature,
                "signedAt": signed_at_ms,
                "nonce": nonce,
            },
        }

    async def _reader(self) -> None:
        assert self._ws is not None
        try:
            async for raw in self._ws:
                frame = json.loads(raw)
                await self._handle_frame(frame)
        except websockets.ConnectionClosed:
            for fut in self._pending.values():
                if not fut.done():
                    fut.set_exception(OpenClawError("connection closed"))
            for run in self._active_runs.values():
                if not run.done.is_set():
                    run.error = "connection closed"
                    run.done.set()

    async def _handle_frame(self, frame: dict[str, Any]) -> None:
        ftype = frame.get("type")

        if ftype == "event":
            event = frame.get("event")
            if event == "connect.challenge" and self._challenge and not self._challenge.done():
                payload = frame.get("payload") or {}
                self._challenge.set_result(str(payload.get("nonce", "")))
                return
            if event == "agent":
                await self._handle_agent_event(frame.get("payload") or {})
            return

        if ftype == "res":
            req_id = frame.get("id")
            if req_id in self._pending:
                fut = self._pending.pop(req_id)
                if frame.get("ok"):
                    fut.set_result(frame.get("payload"))
                else:
                    err = frame.get("error") or {}
                    message = err.get("message") if isinstance(err, dict) else str(err)
                    fut.set_exception(OpenClawError(message or "request failed"))

    async def _handle_agent_event(self, payload: dict[str, Any]) -> None:
        run_id = str(payload.get("runId", ""))
        if not run_id or run_id not in self._active_runs:
            return
        active = self._active_runs[run_id]
        stream = payload.get("stream")
        data = payload.get("data") or {}

        if stream == "assistant":
            delta = data.get("delta") or data.get("text") or ""
            if delta:
                active.chunks.append(str(delta))
        elif stream == "error":
            active.error = str(data.get("error") or data.get("message") or "agent error")
            active.done.set()
        elif stream == "lifecycle":
            phase = str(data.get("phase", "")).lower()
            if phase in ("end", "complete", "completed", "done"):
                active.done.set()
            elif phase in ("error", "failed", "cancelled"):
                active.error = str(data.get("error") or data.get("message") or phase)
                active.done.set()

    async def _request(self, method: str, params: Any, timeout: float = 60.0) -> Any:
        if not self._ws:
            raise OpenClawError("not connected")
        req_id = str(uuid.uuid4())
        fut: asyncio.Future[Any] = asyncio.get_running_loop().create_future()
        self._pending[req_id] = fut
        await self._ws.send(json.dumps({"type": "req", "id": req_id, "method": method, "params": params}))
        return await asyncio.wait_for(fut, timeout=timeout)

    async def request_move(
        self,
        *,
        message: str,
        session_key: str,
        agent_id: str,
        timeout_seconds: int = 120,
        on_event: Optional[Callable[[dict[str, Any]], None]] = None,
    ) -> AgentResponse:
        if not self._ws:
            await self.connect()

        run_id = str(uuid.uuid4())
        active = _ActiveRun(run_id=run_id)
        self._active_runs[run_id] = active

        scoped_key = session_key if session_key.startswith("agent:") else f"agent:{agent_id}:{session_key}"
        agent_params = {
            "message": message,
            "sessionKey": scoped_key,
            "agentId": agent_id,
            "idempotencyKey": run_id,
            "timeout": timeout_seconds,
        }

        try:
            result = await self._request("agent", agent_params, timeout=timeout_seconds + 15)
            try:
                await asyncio.wait_for(active.done.wait(), timeout=timeout_seconds + 15)
            except asyncio.TimeoutError:
                pass

            text = "".join(active.chunks).strip()
            if not text and isinstance(result, dict):
                for key in ("payloads",):
                    payloads = result.get(key)
                    if isinstance(payloads, list):
                        text = "\n".join(
                            str(p.get("text", "")) for p in payloads if isinstance(p, dict) and p.get("text")
                        ).strip()
                nested = result.get("result")
                if not text and isinstance(nested, dict):
                    payloads = nested.get("payloads")
                    if isinstance(payloads, list):
                        text = "\n".join(
                            str(p.get("text", "")) for p in payloads if isinstance(p, dict) and p.get("text")
                        ).strip()

            if active.error and not text:
                raise OpenClawError(active.error)

            return AgentResponse(text=text, raw=result if isinstance(result, dict) else None)
        finally:
            self._active_runs.pop(run_id, None)

    async def close(self) -> None:
        if self._reader_task:
            self._reader_task.cancel()
            self._reader_task = None
        if self._ws:
            await self._ws.close()
            self._ws = None
