from __future__ import annotations

import argparse
import sys
from pathlib import Path

from game_hub import __version__
from game_hub.config import load_config, save_default_config
from game_hub.games.chess import ChessMode
from game_hub.logging.game_logger import GameLogger
from game_hub.openclaw.test_connection import test_connection
from game_hub.replay import replay_game
from game_hub.session import GameSession, OpponentMode
from game_hub.storage.save import create_game, load_saved_game, new_game_id


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="game-hub",
        description="Terminal Game Hub — play board games against OpenClaw",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--config", type=Path, help="Path to config.yaml")

    sub = parser.add_subparsers(dest="command")

    play = sub.add_parser("play", help="Start a new game")
    play.add_argument("game", choices=["tictactoe", "checkers", "chess"])
    play.add_argument(
        "--opponent",
        choices=["openclaw", "human"],
        default="openclaw",
        help="Opponent type (default: openclaw)",
    )
    play.add_argument("--human-side", help="Your side (e.g. X, red, white)")
    play.add_argument(
        "--chess-mode",
        choices=[ChessMode.OPENCLAW.value, ChessMode.STOCKFISH.value],
        default=ChessMode.OPENCLAW.value,
        help="Chess: openclaw (A, default) or stockfish (B)",
    )

    sub.add_parser("menu", help="Interactive game selection menu")

    resume = sub.add_parser("resume", help="Resume a saved game")
    resume.add_argument("save_file", type=Path)

    replay = sub.add_parser("replay", help="Replay a saved game")
    replay.add_argument("save_file", type=Path)
    replay.add_argument("--delay", type=float, default=0.8)

    sub.add_parser("init-config", help="Create default ~/.game-hub/config.yaml")
    sub.add_parser("test-connection", help="Test OpenClaw Gateway + agent JSON response")

    args = parser.parse_args(argv)

    if args.command == "init-config":
        print(f"Created config at {save_default_config()}")
        return

    config = load_config(args.config)

    if args.command == "test-connection":
        sys.exit(test_connection(config))

    if args.command == "replay":
        replay_game(args.save_file, delay=args.delay)
        return

    if args.command == "resume":
        _resume_game(config, args.save_file)
        return

    if args.command == "menu" or args.command is None:
        _interactive_menu(config)
        return

    if args.command == "play":
        _start_new_game(config, args.game, args.opponent, args.human_side, args.chess_mode)
        return

    parser.print_help()


def _default_sides(game: str) -> tuple[str, str]:
    if game == "tictactoe":
        return "X", "O"
    if game == "checkers":
        return "red", "black"
    return "white", "black"


def _start_new_game(
    config,
    game: str,
    opponent: str,
    human_side: str | None,
    chess_mode: str = ChessMode.OPENCLAW.value,
) -> None:
    default_human, default_ai = _default_sides(game)
    hs = human_side or default_human
    ai = default_ai if hs == default_human else default_human

    game_obj = create_game(
        game,
        human_side=hs,
        ai_side=ai,
        stockfish_path=config.stockfish_path,
        chess_mode=chess_mode,
    )
    session = GameSession(
        game_id=new_game_id(),
        game=game_obj,
        human_side=hs,
        ai_side=ai,
        opponent_mode=OpponentMode(opponent),
        config=config,
        logger=GameLogger(config.log_dir),  # type: ignore[arg-type]
        chess_mode=chess_mode,
    )
    session.run_interactive()


def _resume_game(config, save_file: Path) -> None:
    game_id, game, metadata = load_saved_game(save_file)
    session = GameSession(
        game_id=game_id,
        game=game,
        human_side=metadata.get("human_side", "X"),
        ai_side=metadata.get("ai_side", "O"),
        opponent_mode=OpponentMode(metadata.get("opponent_mode", "openclaw")),
        config=config,
        logger=GameLogger(config.log_dir),  # type: ignore[arg-type]
        chess_mode=metadata.get("chess_mode", ChessMode.OPENCLAW.value),
    )
    session.run_interactive()


def _interactive_menu(config) -> None:
    print("\n=== Terminal Game Hub ===\n")
    print("1) Tic-Tac-Toe vs OpenClaw")
    print("2) Checkers vs OpenClaw")
    print("3) Chess vs OpenClaw (Mode A — agent learns to play)")
    print("4) Chess vs Stockfish + OpenClaw commentary (Mode B)")
    print("5) Human vs Human")
    print("6) Resume saved game")
    print("7) Replay saved game")
    print("8) Test OpenClaw connection")
    print("9) Exit")
    choice = input("\nSelect: ").strip()

    if choice == "1":
        _start_new_game(config, "tictactoe", "openclaw", None)
    elif choice == "2":
        _start_new_game(config, "checkers", "openclaw", None)
    elif choice == "3":
        _start_new_game(config, "chess", "openclaw", None, ChessMode.OPENCLAW.value)
    elif choice == "4":
        _start_new_game(config, "chess", "openclaw", None, ChessMode.STOCKFISH.value)
    elif choice == "5":
        game = input("Game (tictactoe/checkers/chess) [tictactoe]: ").strip() or "tictactoe"
        if game not in ("tictactoe", "checkers", "chess"):
            print("Unknown game.")
            return
        _start_new_game(config, game, "human", None)
    elif choice == "6":
        saves = sorted((config.data_dir / "saves").glob("*.json"))
        if not saves:
            print("No saved games.")
            return
        for i, path in enumerate(saves):
            print(f"{i + 1}) {path.name}")
        _resume_game(config, saves[int(input("Pick save: ").strip()) - 1])
    elif choice == "7":
        saves = sorted((config.data_dir / "saves").glob("*.json"))
        if not saves:
            print("No saved games.")
            return
        for i, path in enumerate(saves):
            print(f"{i + 1}) {path.name}")
        replay_game(saves[int(input("Pick save: ").strip()) - 1])
    elif choice == "8":
        sys.exit(test_connection(config))
    else:
        print("Goodbye.")


if __name__ == "__main__":
    main()
