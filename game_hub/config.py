from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml

DEFAULT_DATA_DIR = Path.home() / ".game-hub"
DEFAULT_CONFIG_PATH = DEFAULT_DATA_DIR / "config.yaml"


@dataclass
class OpenClawConfig:
    url: str = "ws://127.0.0.1:18789"
    token: str = ""
    agent_id: str = "main"
    session_key: str = "game-hub"
    timeout_seconds: int = 120
    tls_fingerprint: Optional[str] = None


@dataclass
class HubConfig:
    data_dir: Path = field(default_factory=lambda: DEFAULT_DATA_DIR)
    openclaw: OpenClawConfig = field(default_factory=OpenClawConfig)
    stockfish_path: str = "stockfish"
    log_dir: Optional[Path] = None

    def __post_init__(self) -> None:
        if self.log_dir is None:
            self.log_dir = self.data_dir / "logs"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)


def _merge_openclaw(data: dict[str, Any]) -> OpenClawConfig:
    oc = data.get("openclaw", {}) or {}
    return OpenClawConfig(
        url=os.environ.get("OPENCLAW_GATEWAY_URL", oc.get("url", "ws://127.0.0.1:18789")),
        token=os.environ.get("OPENCLAW_GATEWAY_TOKEN", oc.get("token", "")),
        agent_id=oc.get("agent_id", "main"),
        session_key=oc.get("session_key", "game-hub"),
        timeout_seconds=int(oc.get("timeout_seconds", 120)),
        tls_fingerprint=oc.get("tls_fingerprint"),
    )


def load_config(path: Optional[Path] = None) -> HubConfig:
    config_path = path or DEFAULT_CONFIG_PATH
    data: dict[str, Any] = {}
    if config_path.exists():
        with config_path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}

    data_dir = Path(data.get("data_dir", DEFAULT_DATA_DIR)).expanduser()
    return HubConfig(
        data_dir=data_dir,
        openclaw=_merge_openclaw(data),
        stockfish_path=os.environ.get("STOCKFISH_PATH", data.get("stockfish_path", "stockfish")),
        log_dir=Path(data["log_dir"]).expanduser() if data.get("log_dir") else None,
    )


def save_default_config(path: Optional[Path] = None) -> Path:
    config_path = path or DEFAULT_CONFIG_PATH
    config_path.parent.mkdir(parents=True, exist_ok=True)
    if config_path.exists():
        return config_path

    example = """# Terminal Game Hub configuration
# See docs/OPENCLAW_AGENT_GUIDE.md for setup instructions.

data_dir: ~/.game-hub

openclaw:
  # Direct WebSocket URL — no SSH tunnel required when gateway is reachable on LAN/Tailnet.
  # Examples:
  #   ws://192.168.1.50:18789
  #   wss://my-gateway.example.ts.net:18789
  url: ws://127.0.0.1:18789

  # Gateway auth token (gateway.auth.token on the OpenClaw host).
  # Can also be set via OPENCLAW_GATEWAY_TOKEN environment variable.
  token: ""

  agent_id: main
  session_key: game-hub
  timeout_seconds: 120

  # Optional: pin TLS cert for wss:// remote gateways
  # tls_fingerprint: ""

# Path to Stockfish binary (used for chess move generation)
stockfish_path: stockfish
"""
    config_path.write_text(example, encoding="utf-8")
    return config_path
