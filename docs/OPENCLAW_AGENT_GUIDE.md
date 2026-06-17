# Terminal Game Hub — OpenClaw Agent Guide

This document explains to an OpenClaw instance what the **Terminal Game Hub** is, how it connects, and what your role is when participating in games.

## What is the Terminal Game Hub?

The Terminal Game Hub is a **Python terminal application** that runs on Linux (typically a Raspberry Pi). It is the **authoritative game server**:

- It renders the board in the terminal for the human player.
- It validates every move through a **Move Gate** — illegal moves are never applied.
- It logs every turn to JSONL files.
- It saves and replays games from move history.

**You (OpenClaw) are not the game server.** You are an opponent, strategist, commentator, or analyst. The hub sends you game state; you reply with a proposed move (or commentary). The hub validates your move locally and rejects illegal proposals.

## How connection works (no SSH)

The game hub connects to your **OpenClaw Gateway** as a WebSocket **operator client**. This is the same protocol used by the OpenClaw CLI, Control UI, and macOS app — documented at [docs.openclaw.ai/gateway/protocol](https://docs.openclaw.ai/gateway/protocol).

```
Game Hub (any Linux host)  ──ws:// or wss://──►  OpenClaw Gateway :18789
                              token auth
                              device pairing (one-time)
```

### Network options (device-independent)

| Setup | Game hub `openclaw.url` | Notes |
|-------|-------------------------|-------|
| Same machine | `ws://127.0.0.1:18789` | Loopback; device may auto-approve |
| Home LAN | `ws://192.168.x.x:18789` | Gateway `bind: "lan"` + token auth |
| Tailnet | `wss://hostname.tailnet:18789` | Recommended for remote; no SSH |
| VPS / always-on server | `wss://your-server:18789` | Pin TLS fingerprint optional |

**SSH tunnels are not required.** The hub uses direct WebSocket + shared gateway token + device identity, the same model described in [docs.openclaw.ai/gateway/remote](https://docs.openclaw.ai/gateway/remote) for `transport: "direct"`.

### Authentication flow

1. Hub opens WebSocket to `gateway.url`.
2. Gateway sends `connect.challenge` with a nonce.
3. Hub signs the v3 device auth payload (Ed25519) and sends `connect` with:
   - `role: "operator"`
   - `scopes: ["operator.read", "operator.write"]`
   - `auth.token` = gateway shared secret
   - `device` = stable keypair identity
4. On first connect from a new device ID, gateway requires **device pairing approval**:
   ```bash
   openclaw devices list
   openclaw devices approve <request-id>
   ```
5. Gateway returns `hello-ok` with optional `deviceToken` for reconnects.
6. Hub invokes `agent` RPC with structured move prompts.

### Configuration on the game hub side

File: `~/.game-hub/config.yaml`

```yaml
openclaw:
  url: ws://192.168.1.100:18789
  token: <gateway.auth.token from openclaw.json>
  agent_id: main
  session_key: game-hub
  timeout_seconds: 120
```

Environment overrides: `OPENCLAW_GATEWAY_URL`, `OPENCLAW_GATEWAY_TOKEN`.

### Configuration on the OpenClaw side

Ensure your gateway accepts remote connections with token auth:

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

Use the **same token** in the game hub config. Never expose the gateway on the public internet without `wss://` and strong auth.

## Request → response protocol

When it is your turn, the hub sends an `agent` RPC message containing:

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

## Session key

Games use session key: `agent:<agent_id>:game-hub` (default `agent:main:game-hub`).

This isolates game-hub traffic from your other channels. You may see repeated structured prompts in this session — that is expected.

## Operator checklist

1. Gateway running: `openclaw gateway status`
2. Token configured on both sides
3. Game hub device paired: `openclaw devices list`
4. Test: `game-hub test-connection`
5. Play: `game-hub play tictactoe --opponent openclaw`

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `PAIRING_REQUIRED` | `openclaw devices approve <id>` |
| `AUTH_TOKEN_MISMATCH` | Match `gateway.auth.token` and hub `openclaw.token` |
| Connection refused | Check `gateway.bind`, firewall, correct IP/port |
| Timeout on moves | Increase `timeout_seconds`; check model provider auth |
| Invalid move loops | Reply with exact legal move JSON; see prompt legal list |

## Related OpenClaw documentation

- [Gateway protocol](https://docs.openclaw.ai/gateway/protocol)
- [Gateway architecture](https://docs.openclaw.ai/concepts/architecture)
- [Remote access](https://docs.openclaw.ai/gateway/remote)
- [CLI agent command](https://docs.openclaw.ai/cli/agent)

## Files in this project

| File | Purpose |
|------|---------|
| `docs/OPENCLAW_AGENT_PROMPT.md` | Copy-paste system prompt for your agent workspace |
| `README.md` | Human setup guide |
| `~/.game-hub/device.json` | Hub device identity (auto-created) |
| `~/.game-hub/logs/*.jsonl` | Per-turn game logs |
