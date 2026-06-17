# Terminal Game Hub Specification v1

## Purpose

Create a lightweight terminal-based game hub running on a Raspberry Pi 3B that allows a human player to compete against OpenClaw-controlled opponents.

The Raspberry Pi is the authoritative source of game state and rule enforcement.

OpenClaw acts only as an opponent, strategist, commentator, or analyst.

---

# Goals

## Primary Goals

* Play games against OpenClaw
* Prevent illegal AI moves
* Log all gameplay
* Support replay and analysis
* Operate over a simple network connection to OpenClaw

## Non-Goals

* Real-time games
* Physics simulation
* Graphical UI
* Multiplayer networking
* Cloud-hosted game state

---

# Supported Games

## Phase 1

* Tic-Tac-Toe
* Checkers
* Chess

## Future Expansion

Additional games may be added through the game engine interface.

---

# Core Architecture

## Raspberry Pi Responsibilities

The Raspberry Pi owns:

* Terminal rendering
* User input
* Game state
* Move validation
* Save/load functionality
* Replay generation
* Move logging

The Raspberry Pi is the source of truth.

## OpenClaw Responsibilities

OpenClaw may:

* Select moves
* Provide commentary
* Analyze games
* Review completed games

OpenClaw does not:

* Validate moves
* Store authoritative game state
* Override game rules

---

# Move Gate System

Every move must pass through the Move Gate.

## Flow

1. Move proposed
2. Rules engine validates move
3. Move accepted or rejected
4. Game state updated
5. Move logged

## Accepted Move

If legal:

* Apply move
* Save move
* Update board
* Continue game

## Rejected Move

If illegal:

* Reject move
* Record rejection
* Return error
* Request replacement move

Illegal moves are never applied.

---

# Game Engine Contract

Every game must implement:

```python
get_state()
render()
validate_move()
apply_move()
legal_moves()
is_game_over()
winner()
```

This creates a common interface for all games.

---

# OpenClaw Communication

## Model

Request → Response

No streaming required.

## Request Data

* Game type
* Board state
* Side to play
* Move history (optional)
* Legal move list

## Response Data

* Proposed move
* Optional commentary

## Validation

All responses are validated locally.

Invalid responses trigger another move request.

---

# Logging System

Every turn is recorded.

## Required Fields

* game_id
* game_type
* turn_number
* actor
* move
* legal
* rejection_reason
* board_state_before
* board_state_after
* timestamp

---

# Storage

## Save Format

JSON

## Stored Data

* Game state
* Move history
* Metadata

## Replay Support

A saved game must be replayable from move history alone.

---

# AI Strategy

## Tic-Tac-Toe

OpenClaw may generate moves directly.

## Checkers

OpenClaw may generate moves directly.

If hallucination rates become unacceptable:

* Local minimax becomes primary
* OpenClaw becomes commentary

## Chess

Primary move engine:

* Stockfish

OpenClaw role:

* Commentary
* Coaching
* Analysis

Stockfish remains the move authority.

---

# Failure Handling

## OpenClaw Unavailable

Fallback modes:

* Retry
* Local AI
* Human-vs-human

Game continues without losing state.

## Invalid Response

* Log event
* Request replacement move

---

# Future Features

* Elo ratings
* Match statistics
* AI coaching mode
* Replay viewer
* Opening analysis
* Training puzzles
* Tournament mode

---

# Success Criteria

The project is successful when:

1. A user can launch the hub from a Linux terminal.
2. Tic-Tac-Toe, Checkers, and Chess are playable.
3. OpenClaw can participate as an opponent.
4. Illegal moves are impossible.
5. Every game is logged.
6. Games can be saved and replayed.
7. The system runs reliably on a Raspberry Pi 3B.
