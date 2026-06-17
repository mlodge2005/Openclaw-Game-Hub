"""Tests for checkers coordinates and board display."""

from __future__ import annotations

import unittest

from game_hub.display.board import internal_rank, internal_row_from_rank, render_checkers_board
from game_hub.games.checkers import Checkers


class CheckersCoordinateTests(unittest.TestCase):
    def test_rank_mapping(self):
        self.assertEqual(internal_rank(7), 1)
        self.assertEqual(internal_rank(0), 8)
        self.assertEqual(internal_row_from_rank(3), 5)

    def test_parse_and_format_use_same_notation(self):
        game = Checkers()
        game.board = [["." for _ in range(8)] for _ in range(8)]
        game.board[5][0] = "r"
        game.board[2][1] = "b"
        game.side_to_play = "red"
        legal = game.legal_moves()
        self.assertIn("a3-b4", legal)
        result = game.apply_move("a3-b4", "red")
        self.assertTrue(result.accepted)

    def test_render_uses_chess_coordinates(self):
        game = Checkers(human_side="red")
        text = game.render()
        self.assertIn("a b c d e f g h", text)
        self.assertIn("8 |", text)
        self.assertIn("1 |", text)
        self.assertNotIn("0 |", text)

    def test_render_has_border(self):
        game = Checkers()
        text = render_checkers_board(game.board, human_side="red")
        self.assertIn("+-----------------+", text)


if __name__ == "__main__":
    unittest.main()
