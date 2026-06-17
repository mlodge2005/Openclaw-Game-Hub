# Raspberry Pi install & updates

Raspberry Pi OS / Debian blocks system-wide `pip` (PEP 668). **Always use a venv** in the repo — do not use `pip install --break-system-packages`.

## First-time setup on the Pi

```bash
cd ~/Openclaw-Game-Hub
git pull origin main

# One-time: create venv (needs python3-venv if this fails)
sudo apt install -y python3-venv python3-full
python3 -m venv .venv

source .venv/bin/activate
pip install -U pip
pip install -e .

game-hub init-config
# Edit ~/.game-hub/config.yaml — openclaw.base_url and token
game-hub test-connection
```

Optional: add to your shell so `game-hub` works after `cd` into the repo:

```bash
echo 'alias game-hub="~/Openclaw-Game-Hub/.venv/bin/game-hub"' >> ~/.bashrc
```

Or always activate before play:

```bash
cd ~/Openclaw-Game-Hub && source .venv/bin/activate
```

## Updating after `git pull` (you already pulled — do this)

```bash
cd ~/Openclaw-Game-Hub
git pull origin main
source .venv/bin/activate
pip install -e .
game-hub test-connection
```

If `.venv` does not exist yet, run the **First-time setup** block above instead of only `pip install -e .`.

## What your log means

| Step | Your result |
|------|-------------|
| `git pull` | OK — you have commit `212ed0a` (checkers UI) |
| `pip install -e .` (no venv) | **Expected failure** on Pi OS — use venv |
| `game-hub test-connection` | OK — gateway reachable |

Until you `pip install -e .` **inside `.venv`**, the `game-hub` on your PATH may still be an **old install** without the new board UI. After venv install, run:

```bash
source .venv/bin/activate
which game-hub    # should show .../Openclaw-Game-Hub/.venv/bin/game-hub
game-hub play checkers --opponent openclaw
```

Saved games stay in `~/.game-hub/saves/`.

## ASCII pieces (optional)

```bash
export GAME_HUB_ASCII_PIECES=1
game-hub play checkers --opponent openclaw
```
