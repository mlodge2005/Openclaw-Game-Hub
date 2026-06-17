from game_hub.games.tictactoe import TicTacToe
from game_hub.engine.move_gate import MoveGate
from game_hub.openclaw.prompts import parse_move_response

e = TicTacToe()
g = MoveGate(e, "test")
assert g.propose_move("5", "X").accepted
assert not g.propose_move("5", "O").accepted
m, _ = parse_move_response('{"move": "3"}', ["1", "3"])
assert m == "3"
print("ok")
