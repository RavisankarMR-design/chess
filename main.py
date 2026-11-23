"""Chess move helper (tap moves) + learning course for Render.
Stateless: the phone sends the full move list / position each time."""
import os, shutil, threading
from pathlib import Path

import chess
import chess.engine
from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse

HERE = Path(__file__).parent
SF = os.environ.get("STOCKFISH") or shutil.which("stockfish") or "/usr/games/stockfish"
THINK = float(os.environ.get("THINK_SECS", "3"))
GRADE = float(os.environ.get("GRADE_SECS", "0.3"))  # per analysis when grading a training move

app = FastAPI()
app.add_middleware(GZipMiddleware, minimum_size=1000)
engine = None
lock = threading.Lock()

# bot strength levels for training games: (engine options, search limit)
LEVELS = [
    ({"Skill Level": 0}, chess.engine.Limit(depth=1)),                                     # 0 beginner
    ({"Skill Level": 4}, chess.engine.Limit(depth=4, time=0.2)),                           # 1 easy
    ({"UCI_LimitStrength": True, "UCI_Elo": 1500}, chess.engine.Limit(time=0.3)),          # 2 medium
    ({"UCI_LimitStrength": True, "UCI_Elo": 2000}, chess.engine.Limit(time=0.4)),          # 3 hard
    ({}, chess.engine.Limit(time=0.5)),                                                    # 4 full strength
]
RESET = {"Skill Level": 20, "UCI_LimitStrength": False}


def with_engine(fn):
    """Run fn(engine) under the lock; restart the engine once if it died."""
    global engine
    with lock:
        for attempt in (0, 1):
            try:
                if engine is None:
                    engine = chess.engine.SimpleEngine.popen_uci(SF)
                    engine.configure({"Threads": int(os.environ.get("THREADS", 1)),
                                      "Hash": int(os.environ.get("HASH", 64))})
                return fn(engine)
            except chess.engine.EngineError:
                engine = None
                if attempt:
                    raise


def fmt(sc):
    return f"M{sc.mate()}" if sc.is_mate() else f"{sc.score() / 100:+.2f}"


def best_move(b):
    info = with_engine(lambda e: e.analyse(b, chess.engine.Limit(time=THINK)))
    mv = info["pv"][0]
    return {"uci": mv.uci(), "san": b.san(mv), "eval": fmt(info["score"].pov(b.turn))}


def parse_move(b, u):
    """uci string -> legal Move (auto-queen) or None."""
    try:
        m = chess.Move.from_uci(u)
    except ValueError:
        return None
    q = chess.Move(m.from_square, m.to_square, chess.QUEEN)  # ponytail: always promotes to queen
    m = q if q in b.legal_moves else m
    return m if m in b.legal_moves else None


@app.get("/")
def index():
    return FileResponse(HERE / "tap.html")


@app.get("/learn")
def learn():
    return FileResponse(HERE / "learn.html")


@app.get("/puzzles.json")
def puzzles():
    return FileResponse(HERE / "puzzles.json", headers={"Cache-Control": "public, max-age=86400"})


@app.get("/health")
def health():
    return "ok"


@app.get("/g/state")
def state(color: str = "white", moves: str = ""):
    me = color != "black"
    b, played = chess.Board(), []
    for u in moves.split():
        m = parse_move(b, u)
        if not m:
            return {"err": f"illegal move {u}"}
        b.push(m)
        played.append(m.uci())
    out = {"fen": b.fen(), "me": me, "turn": b.turn, "moves": played, "legal": [m.uci() for m in b.legal_moves],
           "last": played[-1] if played else None, "san": chess.Board().variation_san(b.move_stack) if played else "",
           "best": None, "over": None}
    if b.is_game_over():
        out["over"] = ("Checkmate " if b.is_checkmate() else "Game over ") + b.result()
    elif b.turn == me:
        out["best"] = best_move(b)
    return out


# ---------- coach: turn engine numbers into plain-language reasons ----------
VAL = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 0}
NAME = {chess.PAWN: "pawn", chess.KNIGHT: "knight", chess.BISHOP: "bishop", chess.ROOK: "rook",
        chess.QUEEN: "queen", chess.KING: "king"}


def balance(b, me):
    """material of `me` minus the opponent, in points"""
    return sum(VAL[p.piece_type] * (1 if p.color == me else -1) for p in b.piece_map().values())


def line_san(b, moves):
    t, out = b.copy(), []
    for mv in moves:
        out.append(t.san(mv))
        t.push(mv)
    return " ".join(out)


def hanging(b, me):
    """Most valuable piece of `me` that is attacked and undefended, or attacked by something cheaper."""
    worst = None
    for sq, p in b.piece_map().items():
        if p.color != me or p.piece_type == chess.KING:
            continue
        att = [b.piece_at(a) for a in b.attackers(not me, sq)]
        if not att:
            continue
        cheapest = min(VAL[a.piece_type] or 99 for a in att)
        if not b.attackers(me, sq) or cheapest < VAL[p.piece_type]:
            if not worst or VAL[p.piece_type] > VAL[worst[1].piece_type]:
                worst = (sq, p, min(att, key=lambda a: VAL[a.piece_type] or 99))
    return worst


def explain(b, m, best, before, after, loss):
    """Up to 3 short, predefined coaching messages explaining why a move is good or bad."""
    me, why = b.turn, []
    a = b.copy()
    a.push(m)
    piece = b.piece_at(m.from_square)
    bsc = before["score"].pov(me)
    if a.is_checkmate():
        return ["Checkmate – the king has no escape. Well done!"]
    # 1. missed a forced mate
    if m != best and bsc.is_mate() and bsc.mate() > 0:
        why.append(f"You missed a forced checkmate: {b.san(best)} mates in {bsc.mate()}.")
    if after:
        asc = after["score"].pov(me)
        pv = after.get("pv", [])[:4]
        # 2. allowed a forced mate
        if asc.is_mate() and asc.mate() < 0:
            why.append(f"This allows a forced checkmate: {line_san(a, pv[:3])}. Always check your king's safety.")
        # 3. material the opponent wins by force (engine line)
        elif pv and loss >= 120:
            t = a.copy()
            start = balance(t, me)
            for mv in pv:
                t.push(mv)
            lost = start - balance(t, me)
            first = pv[0]
            cap = a.piece_at(first.to_square)
            if lost >= 2 and cap and cap.color == me:
                why.append(f"After {a.san(first)} you lose your {NAME[cap.piece_type]} on "
                           f"{chess.square_name(first.to_square)} ({line_san(a, pv)}).")
            elif lost >= 2:
                why.append(f"The opponent wins about {lost} points of material: {line_san(a, pv)}.")
    # 4. a piece left hanging (only if nothing explained the loss yet)
    if not why and loss >= 60:
        h = hanging(a, me)
        if h:
            sq, p, att = h
            why.append(f"Your {NAME[p.piece_type]} on {chess.square_name(sq)} is "
                       f"{'unprotected' if not a.attackers(me, sq) else 'attacked by a cheaper piece'} "
                       f"– the {NAME[att.piece_type]} can take it.")
    # 5. what the better move would have done
    if m != best and loss >= 60 and not (bsc.is_mate() and bsc.mate() > 0):
        cap = b.piece_at(best.to_square)
        bb = b.copy()
        bb.push(best)
        if bb.is_checkmate():
            why.append(f"{b.san(best)} was checkmate!")
        elif cap and not b.attackers(not me, best.to_square):
            why.append(f"{b.san(best)} wins a free {NAME[cap.piece_type]}.")
        elif cap:
            why.append(f"{b.san(best)} captures the {NAME[cap.piece_type]} on {chess.square_name(best.to_square)}.")
        elif bb.is_check():
            targets = [bb.piece_at(s) for s in bb.attacks(best.to_square)
                       if bb.piece_at(s) and bb.piece_at(s).color != me and bb.piece_at(s).piece_type != chess.KING]
            big = [t for t in targets if VAL[t.piece_type] >= 3]
            why.append(f"{b.san(best)} is a check" + (f" that also attacks the {NAME[big[0].piece_type]} (a fork)."
                                                      if big else " that keeps the initiative."))
        elif b.is_castling(best):
            why.append(f"{b.san(best)} castles and gets your king safe.")
        else:
            why.append(f"{b.san(best)} keeps a better position (engine eval {fmt(bsc)}).")
    # 6. opening principles (first 10 moves)
    if b.fullmove_number <= 10:
        home = chess.BB_RANK_1 if me else chess.BB_RANK_8
        if piece.piece_type == chess.QUEEN and b.fullmove_number <= 6:
            why.append("Bringing the queen out early lets the opponent attack it and gain time. Develop knights and bishops first.")
        elif piece.piece_type == chess.KING and not b.is_castling(m) and b.has_castling_rights(me):
            why.append("Moving the king loses your right to castle. Castle instead to keep it safe.")
        elif piece.piece_type == chess.KNIGHT and chess.square_file(m.to_square) in (0, 7):
            why.append("A knight on the edge controls fewer squares (“a knight on the rim is dim”).")
        elif piece.piece_type == chess.PAWN and chess.square_file(m.from_square) in (5, 6) and not b.is_capture(m):
            why.append("Pushing the f- or g-pawn early weakens your king's shelter.")
        elif loss <= 60:
            if b.is_castling(m):
                why.append("Good: castling hides your king and brings the rook into play.")
            elif piece.piece_type in (chess.KNIGHT, chess.BISHOP) and chess.BB_SQUARES[m.from_square] & home:
                why.append("Good: develops a piece toward the centre.")
            elif piece.piece_type == chess.PAWN and m.to_square in (chess.E4, chess.D4, chess.E5, chess.D5):
                why.append("Good: a pawn in the centre controls key squares.")
    if not why and loss <= 20 and b.is_capture(m):
        why.append("Good capture.")
    return why[:3]


# ---------- training API (used by /learn) ----------
def pos(b):
    over = b.is_game_over(claim_draw=True)
    return {"fen": b.fen(), "turn": "w" if b.turn else "b", "check": b.is_check(),
            "mate": b.is_checkmate(), "stalemate": b.is_stalemate(), "over": over,
            "result": b.result(claim_draw=True) if over else None,
            "legal": {m.uci(): b.san(m) for m in b.legal_moves}}


@app.get("/t/pos")
def t_pos(fen: str):
    try:
        b = chess.Board(fen)
    except ValueError:
        return {"err": "bad fen"}
    return pos(b)


@app.get("/t/move")
def t_move(fen: str, uci: str, level: int = 4, coach: int = 1, reply: int = 1):
    """Play the trainee's move: grade it (coach), then let the bot reply at `level`."""
    try:
        b = chess.Board(fen)
    except ValueError:
        return {"err": "bad fen"}
    m = parse_move(b, uci)
    if not m:
        return {"err": "illegal move"}
    me, san = b.turn, b.san(m)
    out = {"san": san, "uci": m.uci(), "grade": None, "reply": None}

    def go(e):
        if coach:  # compare the played move with the engine's best, in centipawns from the mover's side
            lim = chess.engine.Limit(time=GRADE)
            before = e.analyse(b, lim)
            best = before["pv"][0]
            after_b = b.copy()
            after_b.push(m)
            after = None
            if after_b.is_checkmate():
                after_cp = 100000
            elif after_b.is_game_over(claim_draw=True):
                after_cp = 0
            else:
                after = e.analyse(after_b, lim)
                after_cp = after["score"].pov(me).score(mate_score=100000)
            best_cp = before["score"].pov(me).score(mate_score=100000)
            loss = 0 if m == best else max(0, best_cp - after_cp)
            verdict = ("best" if m == best else "excellent" if loss <= 20 else "good" if loss <= 60 else
                       "inaccuracy" if loss <= 120 else "mistake" if loss <= 300 else "blunder")
            out["grade"] = {"loss": min(loss, 9999), "verdict": verdict, "best_uci": best.uci(),
                            "best_san": b.san(best), "eval": fmt(before["score"].pov(me)),
                            "why": explain(b, m, best, before, after, loss)}
        b.push(m)
        if reply and not b.is_game_over(claim_draw=True):
            opts, lim = LEVELS[max(0, min(level, 4))]
            try:
                if opts:
                    e.configure(opts)
                r = e.play(b, lim).move
            finally:
                if opts:
                    e.configure(RESET)
            out["reply"] = {"uci": r.uci(), "san": b.san(r)}
            b.push(r)

    with_engine(go)
    out["pos"] = pos(b)
    return out


@app.get("/t/bot")
def t_bot(fen: str, level: int = 4):
    """Bot moves first (used when the trainee plays Black from a White-to-move position)."""
    b = chess.Board(fen)
    opts, lim = LEVELS[max(0, min(level, 4))]

    def go(e):
        try:
            if opts:
                e.configure(opts)
            return e.play(b, lim).move
        finally:
            if opts:
                e.configure(RESET)
    mv = with_engine(go)
    san = b.san(mv)
    b.push(mv)
    return {"uci": mv.uci(), "san": san, "pos": pos(b)}


@app.get("/games.json")
def games():
    return FileResponse(HERE / "games.json", headers={"Cache-Control": "public, max-age=3600"})


@app.get("/t/hint")
def t_hint(fen: str):
    b = chess.Board(fen)
    info = with_engine(lambda e: e.analyse(b, chess.engine.Limit(time=0.5)))
    mv = info["pv"][0]
    return {"uci": mv.uci(), "san": b.san(mv), "eval": fmt(info["score"].pov(b.turn))}
