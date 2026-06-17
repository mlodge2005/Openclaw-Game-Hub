from __future__ import annotations

import json
import re
from typing import List, Optional, Tuple


def parse_move_response(text: str, legal_moves: List[str]) -> Tuple[Optional[str], Optional[str]]:
    """Parse agent reply into (move, commentary). Move must match legal_moves exactly."""
    text = text.strip()
    if not text:
        return None, None

    json_match = re.search(r"\{[\s\S]*\}", text)
    if json_match:
        try:
            data = json.loads(json_match.group())
            move = _normalize_move(str(data.get("move", "")), legal_moves)
            commentary = data.get("commentary")
            if move:
                return move, str(commentary) if commentary else None
            if commentary and not data.get("move"):
                return None, str(commentary)
        except json.JSONDecodeError:
            pass

    for line in text.splitlines():
        m = re.match(r"^\s*move\s*:\s*(.+)\s*$", line, re.IGNORECASE)
        if m:
            move = _normalize_move(m.group(1).strip(), legal_moves)
            if move:
                commentary = "\n".join(
                    ln for ln in text.splitlines() if not re.match(r"^\s*move\s*:", ln, re.IGNORECASE)
                ).strip()
                return move, commentary or None

    legal_lower = {m.lower(): m for m in legal_moves}
    for token in re.findall(r"[a-zA-Z0-9x\-+#=O]+", text):
        normalized = _normalize_move(token, legal_moves)
        if normalized:
            return normalized, text if token != text else None
        if token.lower() in legal_lower:
            return legal_lower[token.lower()], text

    return None, text


def _normalize_move(candidate: str, legal_moves: List[str]) -> Optional[str]:
    candidate = candidate.strip().strip('"').strip("'")
    if not candidate:
        return None
    if candidate in legal_moves:
        return candidate
    lower_map = {m.lower(): m for m in legal_moves}
    if candidate.lower() in lower_map:
        return lower_map[candidate.lower()]
    for legal in legal_moves:
        if legal.lower().startswith(candidate.lower()) or candidate.lower().startswith(legal.lower()):
            return legal
    return None


def build_move_prompt(
    *,
    game_type: str,
    board_render: str,
    side_to_play: str,
    legal_moves: List[str],
    move_history: List[str],
    strategic_context: str = "",
    attempt: int = 1,
    last_error: Optional[str] = None,
) -> str:
    legal_json = json.dumps(legal_moves)
    history_json = json.dumps(move_history[-30:])
    error_line = f"\nYour previous answer was rejected: {last_error}\nRe-analyze and reply again.\n" if last_error else ""
    strategy_block = f"\nStrategic notes:\n{strategic_context}\n" if strategic_context else ""

    return f"""You are playing {game_type} as {side_to_play} in the Terminal Game Hub.

## Your job
Reason strategically over the position — threats, forks, material, tempo, king safety, etc.
Then output exactly ONE move from the legal_moves list below.

You are NOT the rules engine. The hub validates your answer locally.
Your final "move" string must match a legal_moves entry character-for-character.
Do not invent notation. Do not pick randomly.

{error_line}{strategy_block}
## Position
{board_render}

Side to play: {side_to_play}
Move history: {history_json}
Legal moves: {legal_json}

## Response format (JSON only, no markdown fences)
{{"move": "<exactly one entry from legal_moves>", "commentary": "<brief strategic reasoning>"}}
"""
