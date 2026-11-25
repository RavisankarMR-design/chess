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

// ---- blackjack teaching helpers: chart built from bjAdvice so the chart can never disagree with the test ----
const BJ_COL = { H: '#e0b84a', S: '#d9534f', D: '#4a90d9', P: '#3fae6a' }, BJ_NAME = { H: 'Hit', S: 'Stand', D: 'Double', P: 'Split' };
function bjChartH(kind) {
  const C = r => ({ r, s: 0 }), ups = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11];
  const rows = [];
  if (kind === 'hard') for (let t = 17; t >= 8; t--) rows.push([t === 17 ? '17+' : t === 8 ? '8 or less' : t, t >= 12 ? [C(10), C(t - 10)] : [C(2), C(t - 2)]]);
  if (kind === 'soft') for (let x = 9; x >= 2; x--) rows.push(['A,' + x + ' (soft ' + (11 + x) + ')', [C(14), C(x)]]);
  if (kind === 'pair') for (let p = 11; p >= 2; p--) rows.push([p === 11 ? 'A,A' : p + ',' + p, [C(p === 11 ? 14 : p), C(p === 11 ? 14 : p)]]);
  const cell = (h, u) => { const m = bjAdvice(h, u, true, kind === 'pair'); return `<td style="background:${BJ_COL[m]};color:#111;text-align:center;font-weight:700;padding:4px 0">${m}</td>`; };
  return `<table style="min-width:340px"><tr><th>You \\ Dealer</th>${ups.map(u => `<th style="text-align:center;padding:4px 0">${u === 11 ? 'A' : u}</th>`).join('')}</tr>`
    + rows.map(([l, h]) => `<tr><th style="white-space:nowrap">${l}</th>${ups.map(u => cell(h, u)).join('')}</tr>`).join('')
    + `</table><div class="dim" style="font-size:13px;margin-top:4px">${Object.entries(BJ_COL).map(([k, c]) => `<span style="background:${c};color:#111;padding:1px 6px;border-radius:4px;font-weight:700">${k}</span> ${BJ_NAME[k]}`).join(' &nbsp; ')}`
    + (kind === 'pair' ? ' &nbsp; (5,5 is never split: play it as hard 10)' : kind === 'hard' ? '' : ' &nbsp; (D when you cannot double: hit, except soft 18 where you stand)') + '</div>';
}
// one-sentence reason for the correct move, used when the drill answer is wrong
function bjWhy(h, up, m) {
  const { total, soft } = bjVal(h), pair = h.length === 2 && pv(h[0]) === pv(h[1]), weak = up <= 6, U = up === 11 ? 'Ace' : up, p = pair ? pv(h[0]) : 0;
  if (pair && p !== 5) {
    const R = { 11: 'Always split Aces: 12 is a poor total, but each Ace starts a hand that can make 21.', 8: 'Always split 8s: 16 is the worst hand in the game, two hands starting on 8 are far better.',
      10: 'Never split tens: 20 is already a very strong hand.', 9: m === 'P' ? 'Split 9s against a weak card or an 8/9: two hands starting at 9 beat one 18.' : 'Keep 18 against a 7 (dealer likely has 17), 10 or Ace.',
      7: m === 'P' ? 'Split 7s against 2-7: 14 is a stiff hand, two 7s do better.' : '14 against a strong 8-A: split would put more money out. Treat it as a hard 14 and hit.',
      6: m === 'P' ? 'Split 6s against the weak 2-6: 12 is poor and the dealer busts often.' : 'Against 7-A the dealer is strong, so play 12 as a hard hand and hit.',
      4: m === 'P' ? 'Split 4s only against 5 or 6, the dealer\'s two weakest cards.' : 'Do not split 4s (8 total is a hit hand). Hit.' }[p] || (m === 'P' ? 'Split 2s and 3s against 2-7, the dealer\'s weak-to-middling cards.' : 'Against 8-A do not split 2s/3s: hit as a hard 4-6.');
    return R;
  }
  if (pair && p === 5) return '5,5 is a hard 10, never a pair. Double against 2-9, hit against 10 or Ace.';
  if (soft) {
    if (total >= 19) return 'Soft 19-20 is already strong. Stand.';
    if (total === 18) return m === 'D' ? 'Soft 18 against a weak 3-6: double, you cannot bust and the dealer often does.' : m === 'S' ? 'Soft 18 against 2, 7 or 8: stand, 18 beats the dealer\'s likely total.' : 'Soft 18 against 9, 10 or Ace: 18 loses too often, hit (you cannot bust on one card).';
    if (total === 17) return m === 'D' ? 'Soft 17 against 3-6: double.' : 'Soft 17 is weak. Never stand: hit, or double against 3-6.';
    return m === 'D' ? 'Soft 13-16: the Ace protects you from busting, so double only when the dealer is weakest (4-6, or 5-6 for 13-14).' : 'Soft 13-16 against this card: just hit, the Ace means you cannot bust.';
  }
  if (total >= 17) return 'Hard 17 or more: stand. Hitting risks busting too often.';
  if (total >= 13) return weak ? 'Hard 13-16 against a weak 2-6: stand and let the dealer bust (they bust 35-42%).' : 'Hard 13-16 against a strong ' + U + ': standing loses to the dealer\'s likely 17+, so you must hit.';
  if (total === 12) return up >= 4 && up <= 6 ? '12 against 4-6: stand, dealer busts most often.' : '12 against ' + U + ': hit. Only 4, 5, 6 are weak enough to stand.';
  if (total === 11) return m === 'D' ? '11: double against 2-10, the best doubling hand (you hit 21 or 20 with any 9, 10, Ace).' : '11 against an Ace: hit (dealer has blackjack chances and a strong card).';
  if (total === 10) return m === 'D' ? '10: double against 2-9, you beat the dealer\'s card.' : '10 against 10 or Ace: just hit.';
  if (total === 9) return m === 'D' ? '9 against 3-6: double, the dealer is at their weakest.' : '9 against 2 or 7-A: just hit.';
  return '8 or less: you cannot bust, always hit.';
}
// Preflop guide, "everyone folds to you" (open or fold), 6-max. pos 'E' = early (UTG/hijack), 'L' = late (cutoff/button).
// Early ~12% of hands, late ~24%, in line with published 6-max open ranges (UTG 12-17%, CO 25%).
const PK_EARLY = 'AA KK QQ JJ TT 99 88 77 66 AKs AQs AJs ATs KQs KJs KTs QJs QTs JTs T9s AKo AQo AJo KQo'.split(' ');
const PK_LATE = PK_EARLY.concat('55 44 33 22 A9s A8s A7s A6s A5s A4s A3s A2s K9s Q9s J9s T8s 98s 87s 76s 65s 54s ATo KJo KTo QJo QTo JTo'.split(' '));
function pkPre(h, pos) {
  const [a, b] = h.map(c => c.r).sort((x, y) => y - x), su = h[0].s === h[1].s, N = r => ({ 14: 'A', 13: 'K', 12: 'Q', 11: 'J', 10: 'T' }[r] || r);
  const nm = a === b ? N(a) + N(b) : N(a) + N(b) + (su ? 's' : 'o');
  const inE = PK_EARLY.includes(nm), inL = PK_LATE.includes(nm), ok = pos === 'E' ? inE : inL;
  return [ok ? 'R' : 'F', nm, ok ? (pos === 'L' && !inE ? 'Playable only in late position (few players left to act): raise.' : 'Strong enough to open from any seat: raise.')
    : (inL ? 'Playable in late position, too weak from early position: fold.' : 'Not in the opening list even in late position: fold.')];
}
// exact count of unseen cards that lift hero to a straight or better (draw outs)
function pkDrawOuts(hero, board) {
  const used = new Set(hero.concat(board).map(c => c.r * 4 + c.s));
  return newDeck().filter(c => !used.has(c.r * 4 + c.s) && catOf(bestOf(hero.concat(board, [c]))) >= 4).length;
}
if (typeof module !== 'undefined') module.exports = { newDeck, shuffle, bjVal, bjAdvice, hiLo, eval5, catOf, bestOf, equity, needEquity, callEV, BETS, betStats, simulate, RED, CATS, pkPre, PK_EARLY, PK_LATE, pkDrawOuts, bjWhy };
