from __future__ import annotations

import asyncio
import sys
from typing import Optional

from game_hub.config import HubConfig
from game_hub.openclaw.connection_test import print_connection_test, run_connection_test


def test_connection(
    config: HubConfig,
    url: Optional[str] = None,
    token: Optional[str] = None,
) -> int:
    result = asyncio.run(run_connection_test(config, url=url, token=token))
    return print_connection_test(result)
