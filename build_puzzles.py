"""Build puzzles.json from the Lichess puzzle database (CC0, https://database.lichess.org/#puzzles).

Usage (streams only the first rows; the file is already in random order):
  curl -s https://database.lichess.org/lichess_db_puzzle.csv.zst | python build_puzzles.py
Output rows: [id, fen (position the player solves), solution uci moves, rating, themes, opponent's last move]
"""
import csv, io, json, sys
from collections import defaultdict

import chess
import zstandard

PER_BUCKET = 450                      # puzzles per 200-point rating band
BANDS = range(400, 3000, 200)         # 400-599, 600-799, ... 2800-2999
KEEP = {"mateIn1", "mateIn2", "mateIn3", "mateIn4", "fork", "pin", "skewer", "discoveredAttack", "hangingPiece",
        "backRankMate", "smotheredMate", "sacrifice", "deflection", "attraction", "doubleCheck", "trappedPiece",
        "promotion", "advancedPawn", "endgame", "rookEndgame", "pawnEndgame", "queenEndgame", "opening",
        "middlegame", "defensiveMove", "quietMove", "zugzwang", "interference", "xRayAttack", "clearance",
        "capturingDefender", "intermezzo", "exposedKing", "kingsideAttack", "short", "long", "crushing", "mate"}

bucket = defaultdict(list)
need = PER_BUCKET * len(BANDS)
reader = csv.reader(io.TextIOWrapper(zstandard.ZstdDecompressor().stream_reader(sys.stdin.buffer), encoding="utf-8"))
next(reader)  # header: PuzzleId,FEN,Moves,Rating,RatingDeviation,Popularity,NbPlays,Themes,GameUrl,OpeningTags
seen = 0
for row in reader:
    seen += 1
    pid, fen, moves, rating, rd, pop, plays, themes = row[:8]
    rating, rd, pop, plays = int(rating), int(rd), int(pop), int(plays)
    if rd > 90 or pop < 85 or plays < 300:
        continue
    band = (rating - 400) // 200
    if not 0 <= band < len(BANDS) or len(bucket[band]) >= PER_BUCKET:
        continue
    mv = moves.split()
    b = chess.Board(fen)
    first = chess.Move.from_uci(mv[0])
    if first not in b.legal_moves:
        continue
    b.push(first)  # Lichess FEN is before the opponent's move; the player solves after it
    bucket[band].append([pid, b.fen(), mv[1:], rating, [t for t in themes.split() if t in KEEP], mv[0]])
    if sum(len(v) for v in bucket.values()) >= need or seen > 3_000_000:
        break

out = [p for band in sorted(bucket) for p in bucket[band]]
json.dump(out, open("puzzles.json", "w"), separators=(",", ":"))
print(f"scanned {seen} rows, kept {len(out)}:", {BANDS[k]: len(v) for k, v in sorted(bucket.items())}, file=sys.stderr)
