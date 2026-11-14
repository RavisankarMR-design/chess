"""Chess move helper (tap moves) for Render. Stateless: the phone sends the full move list each time."""
import os, shutil, threading
from pathlib import Path

import chess
import chess.engine
from fastapi import FastAPI
from fastapi.responses import FileResponse

HERE = Path(__file__).parent
SF = os.environ.get("STOCKFISH") or shutil.which("stockfish") or "/usr/games/stockfish"
THINK = float(os.environ.get("THINK_SECS", "3"))

app = FastAPI()
engine = None
lock = threading.Lock()


def best_move(b):
    global engine
    with lock:
        for attempt in (0, 1):
            try:
                if engine is None:
                    engine = chess.engine.SimpleEngine.popen_uci(SF)
                    engine.configure({"Threads": 1, "Hash": 64})
                info = engine.analyse(b, chess.engine.Limit(time=THINK))
                break
            except chess.engine.EngineError:  # engine died: restart once
                engine = None
                if attempt:
                    raise
    mv = info["pv"][0]
    sc = info["score"].pov(b.turn)
    return {"uci": mv.uci(), "san": b.san(mv), "eval": f"M{sc.mate()}" if sc.is_mate() else f"{sc.score() / 100:+.2f}"}


@app.get("/")
def index():
    return FileResponse(HERE / "tap.html")


@app.get("/health")
def health():
    return "ok"


@app.get("/g/state")
def state(color: str = "white", moves: str = ""):
    me = color != "black"
    b, played = chess.Board(), []
    for u in moves.split():
        try:
            m = chess.Move.from_uci(u)
        except ValueError:
            return {"err": f"bad move {u}"}
        q = chess.Move(m.from_square, m.to_square, chess.QUEEN)  # ponytail: always promotes to queen
        m = q if q in b.legal_moves else m
        if m not in b.legal_moves:
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
