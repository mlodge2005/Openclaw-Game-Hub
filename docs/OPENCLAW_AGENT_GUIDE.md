# Terminal Game Hub — OpenClaw Agent Guide

This document explains to an OpenClaw instance what the **Terminal Game Hub** is, how it connects, and what your role is when participating in games.

## What is the Terminal Game Hub?

The Terminal Game Hub is a **Python terminal application** that runs on Linux (typically a Raspberry Pi). It is the **authoritative game server**:

- It renders the board in the terminal for the human player.
- It validates every move through a **Move Gate** — illegal moves are never applied.
- It logs every turn to JSONL files.
- It saves and replays games from move history.

**You (OpenClaw) are not the game server.** You are an opponent, strategist, commentator, or analyst. The hub sends you game state; you reply with a proposed move (or commentary). The hub validates your move locally and rejects illegal proposals.

## How connection works

The game hub connects to your **OpenClaw Gateway** over HTTP using the **`/v1/chat/completions`** endpoint — an OpenAI-compatible chat API. This is lightweight (stdlib only, no WebSocket or crypto dependencies) and ideal for Raspberry Pi deployments.

```
Game Hub (any Linux host)  ──HTTP POST──►  OpenClaw Gateway :18789/v1/chat/completions
                              Bearer token auth
                              model: openclaw/<agent_id>
```

### Network options

| Setup | Game hub `openclaw.base_url` | Notes |
|-------|------------------------------|-------|
| Same machine | `http://127.0.0.1:18789` | Loopback |
| Home LAN | `http://192.168.x.x:18789` | Gateway `bind: "lan"` + token auth |
| Tailnet | `https://hostname.tailnet:18789` | Recommended for remote |
| VPS / always-on server | `https://your-server:18789` | Use HTTPS in production |

**SSH tunnels** may be used when the gateway is only reachable via port-forward, but direct HTTP on LAN/Tailnet is preferred.

Legacy `ws://` / `wss://` URLs in config are auto-converted to `http://` / `https://`.

### Authentication

1. Hub POSTs to `{base_url}/v1/chat/completions` with `Authorization: Bearer <token>`.
2. Request body includes `model: "openclaw/<agent_id>"` and the game prompt as a user message.
3. Gateway routes the request to the configured agent and returns an OpenAI-style JSON response.
4. Hub extracts `choices[0].message.content` and parses the move JSON.

No device pairing or Ed25519 signing is required for HTTP auth — only the shared gateway token.

### Configuration on the game hub side

File: `~/.game-hub/config.yaml`

```yaml
openclaw:
  base_url: http://192.168.1.100:18789
  token: <gateway.auth.token from openclaw.json>
  agent_id: main
  timeout_seconds: 120
```

Environment overrides: `OPENCLAW_GATEWAY_URL` (legacy name, accepts `http://` or `ws://`), `OPENCLAW_GATEWAY_TOKEN`.

### Configuration on the OpenClaw side

Ensure your gateway accepts connections with token auth and has the chat completions endpoint enabled:

```json5
{
  gateway: {
    bind: "lan",           // or "tailnet" for Tailscale
    port: 18789,
    auth: {
      mode: "token",
      token: "your-shared-secret"
    }
  }
}
```

Use the **same token** in the game hub config. Never expose the gateway on the public internet without HTTPS and strong auth.

## Request → response protocol

When it is your turn, the hub sends a chat completion request containing:

| Field | Description |
|-------|-------------|
| Game type | `tictactoe`, `checkers`, or `chess` |
| Board render | ASCII board |
| Side to play | Your color/side |
| Move history | Recent moves |
| Legal moves | **Complete list** — you must pick one exactly |

### Required response format

Reply with **JSON only** (no markdown fences):

```json
{"move": "e4", "commentary": "Claiming the center."}
```

- `move` must be **exactly** one entry from the legal moves list.
- `commentary` is optional.

### What happens if you respond incorrectly

1. Hub logs the rejection (including legal_moves at that turn).
2. Hub sends another request with the rejection reason.
3. After 3 failures, the hub shows an **OpenClaw unavailable** error — it does **not** switch to a local AI.

**Illegal moves are never applied.**

## Game-specific roles

### Tic-Tac-Toe

- **You choose moves** from the legal list.
- Board cells are numbered 1–9 or algebraic (A1–C3).

### Checkers

- **You choose moves** from the legal list.
- Notation: `a3-b4` for slides, `a3xc5` for jumps.

### Chess

**Mode A (default):** You select moves from `legal_moves` — the hub validates. Use this to train strategic play.

**Mode B (optional):** Stockfish selects moves; you provide commentary/analysis when prompted.

## Operator checklist

1. Gateway running: `openclaw gateway status`
2. `/v1/chat/completions` endpoint enabled on the gateway
3. Token configured on both sides
4. Test: `game-hub test-connection`
5. Play: `game-hub play tictactoe --opponent openclaw`

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `401 auth rejected` | Match `gateway.auth.token` and hub `openclaw.token` |
| `404 endpoint not found` | Enable `/v1/chat/completions` on the gateway |
| Connection refused | Check `gateway.bind`, firewall, correct IP/port |
| Timeout on moves | Increase `timeout_seconds`; check model provider auth |
| Invalid move loops | Reply with exact legal move JSON; see prompt legal list |

## Related OpenClaw documentation

- [Gateway architecture](https://docs.openclaw.ai/concepts/architecture)
- [Remote access](https://docs.openclaw.ai/gateway/remote)
- [CLI agent command](https://docs.openclaw.ai/cli/agent)

## Files in this project

| File | Purpose |
|------|---------|
| `docs/OPENCLAW_AGENT_PROMPT.md` | Copy-paste system prompt for your agent workspace |
| `README.md` | Human setup guide |
| `~/.game-hub/logs/*.jsonl` | Per-turn game logs |
