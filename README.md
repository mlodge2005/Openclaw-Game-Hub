# Terminal Game Hub

A lightweight terminal game hub for Linux (including Raspberry Pi 3B) where **you** play board games against **OpenClaw**-controlled opponents.

The game hub owns all game state, move validation, logging, saves, and replays. OpenClaw connects over the **OpenClaw Gateway WebSocket API** — no SSH tunnels required when the gateway is reachable on your LAN or Tailnet.

## Supported games

| Game | AI opponent | Move authority |
|------|---------------|----------------|
| Tic-Tac-Toe | OpenClaw or local minimax | Hub validates all moves |
| Checkers | OpenClaw or local random | Hub validates all moves |
| Chess | Stockfish (+ optional OpenClaw commentary) | Stockfish for moves; hub validates |

## Quick start

```bash
# Install (Python 3.9+)
pip install -e .

# Create default config at ~/.game-hub/config.yaml
game-hub init-config

# Edit config: set openclaw.url and openclaw.token
nano ~/.game-hub/config.yaml

# Test gateway connection (pair device on first connect — see docs)
game-hub test-connection

# Play
game-hub menu
# or
game-hub play tictactoe --opponent openclaw
```

## OpenClaw setup (device-independent)

1. Run OpenClaw Gateway on any host (desktop, server, VPS):
   ```bash
   openclaw gateway
   ```

2. Enable remote access without SSH — bind to LAN or Tailnet and use token auth:
   ```json5
   {
     gateway: {
       bind: "tailnet",  // or "lan"
       auth: { mode: "token", token: "your-secret-token" }
     }
   }
   ```

3. Point the game hub at the gateway directly:
   ```yaml
   openclaw:
     url: ws://192.168.1.50:18789      # LAN
     # url: wss://myhost.tailnet:18789 # Tailnet (preferred for remote)
     token: your-secret-token
   ```

4. On first connect, approve the game hub device on the gateway:
   ```bash
   openclaw devices list
   openclaw devices approve <request-id>
   ```

See [docs/OPENCLAW_AGENT_GUIDE.md](docs/OPENCLAW_AGENT_GUIDE.md) for full setup and [docs/OPENCLAW_AGENT_PROMPT.md](docs/OPENCLAW_AGENT_PROMPT.md) for the agent system prompt.

## Configuration

Environment variables (optional):

| Variable | Purpose |
|----------|---------|
| `OPENCLAW_GATEWAY_URL` | WebSocket URL |
| `OPENCLAW_GATEWAY_TOKEN` | Gateway auth token |
| `STOCKFISH_PATH` | Path to Stockfish binary |

Data directory: `~/.game-hub/` (logs, saves, device identity)

## Commands

```bash
game-hub menu                              # Interactive menu
game-hub play tictactoe --opponent openclaw
game-hub play checkers --opponent local
game-hub play chess --opponent local       # Stockfish
game-hub resume ~/.game-hub/saves/<id>.json
game-hub replay ~/.game-hub/saves/<id>.json
game-hub test-connection
```

## Architecture

```
┌─────────────────┐     WebSocket (token)      ┌──────────────────┐
│  Raspberry Pi   │ ─────────────────────────► │ OpenClaw Gateway │
│  Terminal Hub   │   agent RPC (move request) │  + AI Agent      │
│  (authoritative)│ ◄───────────────────────── │                  │
└─────────────────┘     JSON move response     └──────────────────┘
        │
        ├── Move Gate (validate → apply → log)
        ├── JSON saves + JSONL turn logs
        └── Stockfish (chess moves, local)
```

## License

MIT
# Openclaw-Game-Hub
