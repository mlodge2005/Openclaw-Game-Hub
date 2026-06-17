# Updating Terminal Game Hub on Raspberry Pi

After pulling a new release from GitHub:

```bash
cd ~/Openclaw-Game-Hub   # or your clone path
git pull origin main
pip install -e .         # use pip3 / .venv if you installed in a venv
game-hub test-connection   # optional sanity check
```

If you use a virtual environment:

```bash
cd ~/Openclaw-Game-Hub
git pull origin main
source .venv/bin/activate
pip install -e .
```

Restart any running `game-hub` session (saved games in `~/.game-hub/saves/` are kept).

**Force ASCII pieces** on limited terminals:

```bash
export GAME_HUB_ASCII_PIECES=1
game-hub play checkers --opponent openclaw
```
