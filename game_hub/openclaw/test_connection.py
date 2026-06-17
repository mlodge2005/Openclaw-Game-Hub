"""Connection test — HTTP POST to /v1/chat/completions."""

from __future__ import annotations

from game_hub.config import HubConfig
from game_hub.openclaw.client import OpenClawClient, OpenClawUnavailable


def test_connection(config: HubConfig) -> int:
    """Test connectivity. Returns 0 on success, 1 on failure."""
    client = OpenClawClient(
        base_url=config.openclaw.base_url,
        token=config.openclaw.token,
        agent_id=config.openclaw.agent_id,
        timeout_seconds=15,
        max_retries=1,
    )
    print(f"Testing connection to: {client.base_url}/v1/chat/completions")
    print(f"Target agent: {config.openclaw.agent_id}")
    if not config.openclaw.token:
        print("ERROR: No gateway token configured. Set openclaw.token in config.yaml")
        print("       or export OPENCLAW_GATEWAY_TOKEN.")
        return 1
    try:
        text = client.request_move(message="Reply with exactly: CONNECTION_OK")
    except OpenClawUnavailable as exc:
        print(f"\nFAILED: {exc}")
        if exc.status_code == 404:
            print("\nThe /v1/chat/completions endpoint is not enabled on the Gateway.")
        elif exc.status_code == 401:
            print("\nToken rejected. Check openclaw.token matches gateway.auth.token.")
        else:
            print("\nMake sure: 1) Gateway running  2) SSH tunnel active  3) base_url correct")
        return 1
    print(f"\nSUCCESS: {text}")
    print("Gateway is reachable and the agent responded.\n")
    return 0
