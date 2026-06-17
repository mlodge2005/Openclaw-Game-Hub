from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from game_hub.config import HubConfig
from game_hub.openclaw.client import OpenClawClient, OpenClawError
from game_hub.openclaw.device import load_or_create_device_identity
from game_hub.openclaw.prompts import parse_move_response


@dataclass
class ConnectionTestResult:
    gateway_reachable: bool = False
    token_accepted: bool = False
    device_paired: bool = False
    pairing_required: bool = False
    agent_responded: bool = False
    json_parsed: bool = False
    parsed_move: Optional[str] = None
    gateway_version: Optional[str] = None
    device_id: Optional[str] = None
    error: Optional[str] = None
    pairing_hint: Optional[str] = None

    @property
    def passed(self) -> bool:
        return (
            self.gateway_reachable
            and self.token_accepted
            and not self.pairing_required
            and self.agent_responded
            and self.json_parsed
        )


TEST_LEGAL_MOVES = ["3", "6", "7", "8"]
TEST_PROMPT = """Terminal Game Hub connection test.

Board (Tic-Tac-Toe):
 X | O | 3
---+---+---
 4 | X | 6
---+---+---
 7 | 8 | O

Side to play: O
Move history: ["5", "1", "9", "2"]
Legal moves: ["3", "6", "7", "8"]

Analyze the position. X threatens a win on column 3 — block if possible.
Respond with JSON only:
{"move": "<one of the legal moves exactly>", "commentary": "connection test"}
"""


async def run_connection_test(
    config: HubConfig,
    *,
    url: Optional[str] = None,
    token: Optional[str] = None,
) -> ConnectionTestResult:
    result = ConnectionTestResult()
    device_path = config.data_dir / "device.json"
    identity = load_or_create_device_identity(device_path)
    result.device_id = identity.device_id

    client = OpenClawClient(
        url=url or config.openclaw.url,
        token=token or config.openclaw.token,
        device_identity=identity,
        device_path=device_path,
        tls_fingerprint=config.openclaw.tls_fingerprint,
    )

    try:
        hello = await client.connect()
        result.gateway_reachable = True
        result.token_accepted = True
        result.device_paired = True
        result.gateway_version = (hello.get("server") or {}).get("version")

        response = await client.request_move(
            message=TEST_PROMPT,
            session_key=config.openclaw.session_key,
            agent_id=config.openclaw.agent_id,
            timeout_seconds=min(config.openclaw.timeout_seconds, 90),
        )
        result.agent_responded = bool(response.text.strip())
        move, _ = parse_move_response(response.text, TEST_LEGAL_MOVES)
        if move:
            result.json_parsed = True
            result.parsed_move = move
        else:
            result.error = f"Agent replied but move not parseable. Raw: {response.text[:300]}"
    except OpenClawError as exc:
        msg = str(exc)
        result.error = msg
        if "pairing" in msg.lower() or "PAIRING" in msg:
            result.gateway_reachable = True
            result.pairing_required = True
            result.pairing_hint = (
                "Approve this device on the gateway:\n"
                "  openclaw devices list\n"
                "  openclaw devices approve <request-id>"
            )
        elif "auth" in msg.lower() or "token" in msg.lower():
            result.gateway_reachable = True
    except (OSError, ConnectionError) as exc:
        result.error = f"Gateway not reachable at {url or config.openclaw.url}: {exc}"
    finally:
        try:
            await client.close()
        except Exception:
            pass

    return result


def print_connection_test(result: ConnectionTestResult) -> int:
    checks = [
        ("Gateway reachable", result.gateway_reachable),
        ("Token accepted", result.token_accepted),
        ("Device paired", result.device_paired and not result.pairing_required),
        ("Agent response received", result.agent_responded),
        ("JSON move parsed", result.json_parsed),
    ]

    print("\n=== OpenClaw Connection Test ===\n")
    if result.gateway_version:
        print(f"Gateway version: {result.gateway_version}")
    if result.device_id:
        print(f"Device ID: {result.device_id}")
    print()

    for label, ok in checks:
        mark = "OK" if ok else "FAIL"
        print(f"  [{mark}] {label}")

    if result.parsed_move:
        print(f"\n  Parsed test move: {result.parsed_move}")

    if result.pairing_required and result.pairing_hint:
        print(f"\n{result.pairing_hint}")

    if result.error and not result.passed:
        print(f"\nError: {result.error}")

    if result.passed:
        print("\nAll checks passed. OpenClaw connection is ready for gameplay.")
        return 0

    print("\nConnection test failed. Fix the issues above before playing.")
    return 1
