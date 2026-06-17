"""Device identity stub — not needed for HTTP auth."""

from __future__ import annotations

from typing import NamedTuple


class DeviceIdentity(NamedTuple):
    device_id: str = "game-hub-http"
