"""Self-check for the coach messages. Needs Stockfish: set STOCKFISH=path. Run: python test_coach.py"""
import main

START = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"


def why(fen, uci):
    r = main.t_move(fen=fen, uci=uci, level=4, coach=1, reply=0)
    print(f"{r['san']:6} {r['grade']['verdict']:10} {r['grade']['why']}")
    return " ".join(r["grade"]["why"])


# missed mate in 1
assert "missed a forced checkmate" in why("6k1/5ppp/8/8/8/8/8/R5K1 w - - 0 1", "g1f2")
# allows fool's mate
assert "forced checkmate" in why("rnbqkbnr/pppp1ppp/8/4p3/8/5P2/PPPPP1PP/RNBQKBNR w KQkq - 0 2", "g2g4")
# 1.e4 e5 2.Nf3 Nc6 3.Nxe5?? Nxe5 loses the knight for a pawn
assert "knight" in why("r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3", "f3e5")
# knight to the rim
assert "rim" in why("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", "g1h3")
# early queen
assert "queen out early" in why("rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2", "d1h5")
# praise for a good opening move
assert "Good" in why(START, "e2e4")
# delivering mate
assert "Checkmate" in why("6k1/5ppp/8/8/8/8/8/R5K1 w - - 0 1", "a1a8")
print("OK: coach messages")
main.engine.quit()
