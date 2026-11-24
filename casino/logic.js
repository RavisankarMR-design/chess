// Pure game logic. Loaded by index.html (globals) and test.js (require).
const RANKS = '23456789TJQKA', SUITS = '♠♥♦♣';
const newDeck = () => { const d = []; for (let s = 0; s < 4; s++) for (let r = 2; r <= 14; r++) d.push({ r, s }); return d; };
const shuffle = a => { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; };
const cardStr = c => RANKS[c.r - 2] + SUITS[c.s];

// ---------- Blackjack ----------
const pv = c => c.r === 14 ? 11 : Math.min(c.r, 10);           // point value, ace = 11
const hiLo = c => c.r >= 10 ? -1 : c.r <= 6 ? 1 : 0;            // Hi-Lo count tag (ace is r=14)
function bjVal(h) {
  let t = 0, a = 0;
  for (const c of h) { t += pv(c); if (c.r === 14) a++; }
  while (t > 21 && a) { t -= 10; a--; }
  return { total: t, soft: a > 0 };
}
// Basic strategy: 6 decks, dealer stands on all 17, double after split, no surrender, split once.
// up = dealer upcard point value (2..11). Returns 'H' hit, 'S' stand, 'D' double, 'P' split.
function bjAdvice(h, up, canDouble, canSplit) {
  if (canSplit && h.length === 2 && pv(h[0]) === pv(h[1])) {
    const p = pv(h[0]);
    let m = null;
    if (p === 11 || p === 8) m = 'P';
    else if (p === 10) m = 'S';
    else if (p === 9) m = (up <= 6 || up === 8 || up === 9) ? 'P' : 'S';
    else if (p === 7) m = up <= 7 ? 'P' : 'H';
    else if (p === 6) m = up <= 6 ? 'P' : 'H';
    else if (p === 4) m = (up === 5 || up === 6) ? 'P' : 'H';
    else if (p === 3 || p === 2) m = up <= 7 ? 'P' : 'H';
    if (m) return m;                                            // pair of 5s falls through to hard 10
  }
  const { total, soft } = bjVal(h);
  let m;
  if (soft) {
    if (total >= 19) m = 'S';
    else if (total === 18) m = (up >= 3 && up <= 6) ? 'D' : up <= 8 ? 'S' : 'H';
    else if (total === 17) m = (up >= 3 && up <= 6) ? 'D' : 'H';
    else if (total >= 15) m = (up >= 4 && up <= 6) ? 'D' : 'H';
    else m = (up === 5 || up === 6) ? 'D' : 'H';
  } else {
    if (total >= 17) m = 'S';
    else if (total >= 13) m = up <= 6 ? 'S' : 'H';
    else if (total === 12) m = (up >= 4 && up <= 6) ? 'S' : 'H';
    else if (total === 11) m = up <= 10 ? 'D' : 'H';
    else if (total === 10) m = up <= 9 ? 'D' : 'H';
    else if (total === 9) m = (up >= 3 && up <= 6) ? 'D' : 'H';
    else m = 'H';
  }
  if (m === 'D' && !canDouble) m = (soft && total === 18) ? 'S' : 'H';
  return m;
}

// ---------- Poker ----------
const CATS = ['High card', 'Pair', 'Two pair', 'Three of a kind', 'Straight', 'Flush', 'Full house', 'Four of a kind', 'Straight flush'];
function eval5(c) {
  const r = c.map(x => x.r).sort((a, b) => b - a);
  const flush = c.every(x => x.s === c[0].s);
  const cnt = {}; r.forEach(x => cnt[x] = (cnt[x] || 0) + 1);
  const g = Object.entries(cnt).map(([k, v]) => [+k, v]).sort((a, b) => b[1] - a[1] || b[0] - a[0]);
  let sh = 0;
  if (g.length === 5) { if (r[0] - r[4] === 4) sh = r[0]; else if (r[0] === 14 && r[1] === 5) sh = 5; } // wheel A-2-3-4-5
  const n0 = g[0][1], n1 = g[1] ? g[1][1] : 0;
  let cat;
  if (sh && flush) cat = 8; else if (n0 === 4) cat = 7; else if (n0 === 3 && n1 === 2) cat = 6;
  else if (flush) cat = 5; else if (sh) cat = 4; else if (n0 === 3) cat = 3;
  else if (n0 === 2 && n1 === 2) cat = 2; else if (n0 === 2) cat = 1; else cat = 0;
  const tb = sh ? [sh] : g.map(x => x[0]);
  let s = cat; for (let i = 0; i < 5; i++) s = s * 15 + (tb[i] || 0);
  return s;
}
const catOf = s => Math.floor(s / 15 ** 5);
function bestOf(cards) {                                        // best 5 of 5..7 cards
  let best = -1; const n = cards.length;
  (function rec(start, ch) {
    if (ch.length === 5) { best = Math.max(best, eval5(ch)); return; }
    for (let i = start; i < n; i++) { ch.push(cards[i]); rec(i + 1, ch); ch.pop(); }
  })(0, []);
  return best;
}
// Monte Carlo win equity of hero vs ONE RANDOM opponent hand (ties count half).
function equity(hero, board, n = 1000, opps = 1) {
  const used = new Set(hero.concat(board).map(c => c.r * 4 + c.s));
  const rest = newDeck().filter(c => !used.has(c.r * 4 + c.s));
  const need = 2 * opps + 5 - board.length;
  let w = 0;
  for (let i = 0; i < n; i++) {
    for (let j = 0; j < need; j++) { const k = j + Math.floor(Math.random() * (rest.length - j)); [rest[j], rest[k]] = [rest[k], rest[j]]; }
    const b = board.concat(rest.slice(2 * opps, need)), h = bestOf(hero.concat(b));
    let best = -1, ties = 0;
    for (let o = 0; o < opps; o++) { const s = bestOf(rest.slice(2 * o, 2 * o + 2).concat(b)); if (s > best) { best = s; ties = 1; } else if (s === best) ties++; }
    w += h > best ? 1 : h === best ? 1 / (ties + 1) : 0;
  }
  return w / n;
}
// pot = pot BEFORE villain's bet; hero must call `bet` to win pot+bet.
const needEquity = (pot, bet) => bet / (pot + 2 * bet);
const callEV = (eq, pot, bet) => eq * (pot + bet) - (1 - eq) * bet;

// ---------- Roulette (European, single zero) ----------
const RED = new Set([1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36]);
const BETS = {
  'Red': [1, n => RED.has(n)], 'Black': [1, n => n > 0 && !RED.has(n)],
  'Odd': [1, n => n > 0 && n % 2 === 1], 'Even': [1, n => n > 0 && n % 2 === 0],
  'Low 1-18': [1, n => n >= 1 && n <= 18], 'High 19-36': [1, n => n >= 19],
  '1st dozen': [2, n => n >= 1 && n <= 12], '2nd dozen': [2, n => n >= 13 && n <= 24], '3rd dozen': [2, n => n >= 25],
  'Column 1': [2, n => n > 0 && n % 3 === 1], 'Column 2': [2, n => n > 0 && n % 3 === 2], 'Column 3': [2, n => n > 0 && n % 3 === 0],
  'Straight (one number)': [35, null],                          // win fn built from the picked number
};
const betStats = (pay, win) => {
  let k = 0; for (let n = 0; n <= 36; n++) if (win(n)) k++;
  return { p: k / 37, ev: (k * pay - (37 - k)) / 37 };          // ev per 1 staked
};
// Compare flat betting vs Martingale on Red. Returns avg final bankroll, % ended up, % busted.
function simulate(martingale, trials = 2000, spins = 200, bank0 = 1000, base = 10, maxBet = 500) {
  let sum = 0, up = 0, bust = 0;
  for (let t = 0; t < trials; t++) {
    let bank = bank0, bet = base;
    for (let i = 0; i < spins && bank > 0; i++) {
      const stake = Math.min(bet, bank, maxBet);
      const n = Math.floor(Math.random() * 37);
      if (RED.has(n)) { bank += stake; bet = base; } else { bank -= stake; if (martingale) bet *= 2; }
    }
    sum += bank; if (bank > bank0) up++; if (bank <= 0) bust++;
  }
  return { avg: sum / trials, pctUp: 100 * up / trials, pctBust: 100 * bust / trials };
}

if (typeof module !== 'undefined') module.exports = { newDeck, shuffle, bjVal, bjAdvice, hiLo, eval5, catOf, bestOf, equity, needEquity, callEV, BETS, betStats, simulate, RED };
