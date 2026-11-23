"""Build games.json: annotated games / opening lines for the course viewer. Every move is validated by python-chess.
Run: python build_games.py"""
import json
import chess

START = chess.STARTING_FEN
# id: (title, start fen, "SAN moves", {ply number (1 = first move): comment})
G = {
"opera": ("Morphy vs Duke of Brunswick & Count Isouard, Paris 1858 (the Opera Game)", START,
 "e4 e5 Nf3 d6 d4 Bg4 dxe5 Bxf3 Qxf3 dxe5 Bc4 Nf6 Qb3 Qe7 Nc3 c6 Bg5 b5 Nxb5 cxb5 Bxb5+ Nbd7 O-O-O Rd8 Rxd7 Rxd7 Rd1 Qe6 Bxd7+ Nxd7 Qb8+ Nxb8 Rd8#",
 {1: "White takes the centre.", 4: "Philidor Defence: solid but passive.", 6: "Pinning the knight – but Black will have to give up the bishop pair.",
  8: "Black gives the bishop to avoid losing a pawn; White recaptures with the queen, which now eyes f7 and b7.",
  11: "Developing with a threat: the bishop joins the queen against f7.", 13: "Double attack on b7 and f7!", 14: "Black must defend f7 with the queen, blocking the f8-bishop – Black is falling behind in development.",
  15: "Morphy develops instead of grabbing b7. Development first!", 17: "Pinning the f6-knight to the queen.",
  19: "A sacrifice to open lines while Black's king is still in the centre.", 21: "The b5-bishop pins the d7-knight.",
  23: "Castling queenside brings the rook to the open d-file – every White piece is now active.", 25: "Another sacrifice: the rook removes the d7 defender.",
  27: "Renewing the pin with the last rook.", 29: "Clearing the way for the final blow.",
  31: "Queen sacrifice! It deflects the knight from d7.", 33: "Checkmate with the last remaining pieces – a perfect lesson in development and open lines."}),
"fools": ("Fool's Mate – the fastest checkmate", START, "f3 e5 g4 Qh4#",
 {1: "Weakens the e1–h4 diagonal.", 3: "Opens it completely.", 4: "Checkmate. Lesson: don't push the f- and g-pawns early."}),
"scholars": ("Scholar's Mate – and how to stop it", START, "e4 e5 Qh5 Nc6 Bc4 Nf6 Qxf7#",
 {3: "Queen attacks e5 and f7.", 5: "Bishop + queen both aim at f7, defended only by the king.",
  6: "Mistake! 3...g6 or 3...Qe7 defends.", 7: "Checkmate. Always watch f7 (f2 as White)."}),
"legal": ("Legal's Mate – punishing greed", START, "e4 e5 Nf3 d6 Bc4 Bg4 Nc3 g6 Nxe5 Bxd1 Bxf7+ Ke7 Nd5#",
 {6: "Pinning the knight to the queen.", 8: "A slow move.", 9: "The 'pinned' knight moves anyway! White offers the queen.",
  10: "Greed! 5...dxe5 was necessary.", 11: "Check, driving the king forward.", 13: "Checkmate by three minor pieces."}),
"italian": ("Italian Game: Giuoco Pianissimo (main plan for White)", START,
 "e4 e5 Nf3 Nc6 Bc4 Bc5 c3 Nf6 d3 d6 O-O O-O Re1 a6 Bb3 Ba7 h3 h6 Nbd2 Re8 Nf1 Be6 Ng3",
 {3: "Develops and attacks e5.", 5: "The Italian bishop eyes f7.", 7: "Prepares d4 one day and gives the bishop a retreat on c2/b3.",
  9: "Solid: protects e4 and opens the c1-bishop.", 11: "King safety first.", 13: "The rook supports e4 and the e-file.",
  15: "Keeps the bishop safe from ...Na5 or ...d5 tricks.", 17: "Stops ...Bg4 or ...Ng4.",
  19: "The famous knight manoeuvre: Nbd2–f1–g3, heading for f5 or h5.", 23: "Plan: Nf5, d4, or a slow kingside attack. Typical Italian strategy."}),
"twoknights": ("Two Knights: 4.Ng5 and the Fried Liver trap", START,
 "e4 e5 Nf3 Nc6 Bc4 Nf6 Ng5 d5 exd5 Nxd5 Nxf7 Kxf7 Qf3+ Ke6 Nc3",
 {7: "Attacking f7 twice.", 8: "The best defence: counter-attack in the centre.", 10: "Natural but risky! The correct move is 5...Na5.",
  11: "The Fried Liver sacrifice: knight for pawn to drag the king out.", 13: "Check, attacking the d5-knight too.",
  15: "Piling up on the pinned d5-knight. Black's king is stuck in the centre – a huge attack for White."}),
"ruy": ("Ruy Lopez: Closed main line", START,
 "e4 e5 Nf3 Nc6 Bb5 a6 Ba4 Nf6 O-O Be7 Re1 b5 Bb3 d6 c3 O-O h3 Na5 Bc2 c5 d4",
 {5: "Pressure on the c6-knight, which defends e5.", 6: "The Morphy Defence: asking the bishop.", 9: "Castling: White isn't afraid of ...Nxe4 here.",
  12: "Gaining space and kicking the bishop.", 15: "Preparing d4 and a retreat for the bishop.", 17: "Prevents ...Bg4 pinning the knight.",
  18: "Chigorin plan: chase the bishop, then ...c5.", 21: "White builds the ideal centre. A long strategic battle starts."}),
"qgd": ("Queen's Gambit Declined (Black's solid answer to 1.d4)", START,
 "d4 d5 c4 e6 Nc3 Nf6 Bg5 Be7 e3 O-O Nf3 Nbd7 Rc1 c6 Bd3 dxc4 Bxc4 Nd5",
 {3: "The Queen's Gambit: offering a pawn to deflect d5.", 4: "Declining: Black keeps a firm grip on d5.", 7: "Pinning the f6-knight.",
  8: "Unpinning calmly.", 10: "Black castles quickly.", 12: "Flexible development.", 14: "Strengthening d5 and preparing ...dxc4.",
  16: "Black takes when White's bishop has spent a move – gaining time.", 18: "Capablanca's freeing manoeuvre: trading pieces relieves Black's position."}),
"london": ("London System (an easy setup for White)", START,
 "d4 d5 Bf4 Nf6 e3 e6 Nf3 c5 c3 Nc6 Nbd2 Bd6 Bg3 O-O Bd3 b6 Ne5",
 {3: "The London bishop comes out before e3 locks it in.", 5: "Solid pawn triangle d4–e3–c3 coming.", 9: "Supporting d4 against ...c5 pressure.",
  11: "Knight to d2 keeps c3 for the pawn.", 13: "Avoiding a bishop trade on f4 with doubled pawns.", 15: "Bishop aims at h7.",
  17: "The knight jumps to e5 – a typical London attacking set-up (f4, Qf3, g4 ideas)."}),
"immortal": ("Anderssen vs Kieseritzky, London 1851 (the Immortal Game)", START,
 "e4 e5 f4 exf4 Bc4 Qh4+ Kf1 b5 Bxb5 Nf6 Nf3 Qh6 d3 Nh5 Nh4 Qg5 Nf5 c6 g4 Nf6 Rg1 cxb5 h4 Qg6 h5 Qg5 Qf3 Ng8 Bxf4 Qf6 Nc3 Bc5 Nd5 Qxb2 Bd6 Bxg1 e5 Qxa1+ Ke2 Na6 Nxg7+ Kd8 Qf6+ Nxf6 Be7#",
 {3: "The King's Gambit: a pawn for rapid development and an open f-file.", 6: "Annoying check: White loses the right to castle.",
  8: "Bryan Countergambit: Black returns a pawn to deflect the bishop.", 19: "Gaining space and time against the black queen.",
  21: "White gives up the bishop: development and initiative matter more.", 33: "Attacking the queen and preparing a mating net.",
  35: "White gives up a rook!", 36: "Black grabs it.", 37: "And the other rook too – White blocks the queen's defence of g7.",
  41: "The knight checks; Black's king runs.", 43: "Queen sacrifice!", 45: "Checkmate with three minor pieces after giving away both rooks and the queen."}),
"lucena": ("Lucena position: building a bridge (rook endgame win)", "1K6/1P1k4/8/8/8/8/r7/2R5 w - - 0 1",
 "Rd1+ Ke7 Rd4 Ra1 Kc7 Rc1+ Kb6 Rb1+ Kc6 Rc1+ Kb5 Rb1+ Rb4",
 {1: "Drive the defending king one more file away.", 3: "The key move: the rook goes to the 4th rank to 'build a bridge'.",
  5: "The king steps out; checks from behind start.", 7: "Walking down toward the rook.", 13: "The bridge: the rook blocks the checks. The pawn will promote."}),
"philidor": ("Philidor position: the drawing defence", "4k3/8/r7/4PK2/8/8/8/7R w - - 0 1",
 "Rh7 Rb6 e6 Rb1 Kf6 Rf1+ Ke5 Re1+",
 {0: "Black (defending) keeps the rook on the 6th rank so the White king cannot advance.", 3: "As soon as the pawn reaches the 6th rank, the White king loses its shelter...",
  4: "...so the rook drops to the 1st rank and checks from behind.", 8: "Endless checks: a draw. Remember: 6th rank until the pawn advances, then check from behind."}),
}

out = {}
for gid, (title, fen, sans, comments) in G.items():
    b = chess.Board(fen)
    fens, ucis, sl = [b.fen()], [], []
    for s in sans.split():
        m = b.parse_san(s)  # raises if illegal
        sl.append(b.san(m))
        ucis.append(m.uci())
        b.push(m)
        fens.append(b.fen())
    out[gid] = {"title": title, "fens": fens, "sans": sl, "ucis": ucis, "comments": {str(k): v for k, v in comments.items()},
                "result": b.result() if b.is_game_over() else None}
json.dump(out, open("games.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print({k: (len(v["sans"]), v["result"]) for k, v in out.items()})
