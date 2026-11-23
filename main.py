"""Chess move helper (tap moves) + learning course for Render.
Stateless: the phone sends the full move list / position each time."""
import os, shutil, threading
from pathlib import Path

import chess
import chess.engine
from fastapi import FastAPI
from fastapi.responses import FileResponse

HERE = Path(__file__).parent
SF = os.environ.get("STOCKFISH") or shutil.which("stockfish") or "/usr/games/stockfish"
THINK = float(os.environ.get("THINK_SECS", "3"))
GRADE = float(os.environ.get("GRADE_SECS", "0.3"))  # per analysis when grading a training move

app = FastAPI()
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
            if after_b.is_checkmate():
                after_cp = 100000
            elif after_b.is_game_over(claim_draw=True):
                after_cp = 0
            else:
                after_cp = e.analyse(after_b, lim)["score"].pov(me).score(mate_score=100000)
            best_cp = before["score"].pov(me).score(mate_score=100000)
            loss = 0 if m == best else max(0, best_cp - after_cp)
            verdict = ("best" if m == best else "excellent" if loss <= 20 else "good" if loss <= 60 else
                       "inaccuracy" if loss <= 120 else "mistake" if loss <= 300 else "blunder")
            out["grade"] = {"loss": min(loss, 9999), "verdict": verdict, "best_uci": best.uci(),
                            "best_san": b.san(best), "eval": fmt(before["score"].pov(me))}
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


@app.get("/t/hint")
def t_hint(fen: str):
    b = chess.Board(fen)
    info = with_engine(lambda e: e.analyse(b, chess.engine.Limit(time=0.5)))
    mv = info["pv"][0]
    return {"uci": mv.uci(), "san": b.san(mv), "eval": fmt(info["score"].pov(b.turn))}
