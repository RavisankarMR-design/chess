// Shared visuals for the table pages. Needs logic.js loaded first.
const $ = id => document.getElementById(id);
const pick = a => a[Math.floor(Math.random() * a.length)];
const sleep = ms => new Promise(r => setTimeout(r, ms));
const rk = c => c.r === 10 ? '10' : RANKS[c.r - 2];

// A realistic card face. Face cards show a big letter. Marks a card as shown so it only animates when first dealt.
function faceH(c, back, sm) {
  const cls = (sm ? 'sm ' : '') + (c && !c._s && !back ? 'deal' : '');
  if (c) c._s = true;
  if (back) return `<div class="pcard back ${sm ? 'sm' : ''}"></div>`;
  const s = SUITS[c.s], face = c.r >= 11 && c.r <= 13;
  return `<div class="pcard ${c.s === 1 || c.s === 2 ? 'red' : ''} ${cls}"><span class="ix tl">${rk(c)}<br>${s}</span><span class="mid">${face ? `<em>${RANKS[c.r - 2]}</em><small>${s}</small>` : s}</span><span class="ix br">${rk(c)}<br>${s}</span></div>`;
}
const slotH = sm => `<div class="pcard slot ${sm ? 'sm' : ''}"></div>`;

const DEN = [[500, 'p'], [100, 'k'], [25, 'g'], [5, 'r'], [1, 'w']];
const chipList = n => { const o = []; let r = n; for (const [v, c] of DEN) { const q = Math.floor(r / v); r -= q * v; for (let i = 0; i < q; i++) o.push(c); } return o; };
const chipsH = n => `<span class="chips">${chipList(n).slice(0, 6).map(c => `<span class="chip ${c}"></span>`).join('')}</span>`;
const stackH = n => n ? `<div class="stack">${chipList(n).slice(0, 9).map(c => `<span class="chip ${c}"></span>`).join('')}<b>$${n}</b></div>` : '';
const towersH = n => { const g = {}; chipList(n).forEach(c => g[c] = (g[c] || 0) + 1); return `<div class="towers">${Object.entries(g).map(([c, q]) => `<div class="stack">${Array(Math.min(q, 8)).fill(`<span class="chip ${c}"></span>`).join('')}</div>`).join('')}</div>`; };
const chipBtns = vals => vals.map(v => `<button class="chipb ${DEN.find(d => d[0] === v)[1]}" data-v="${v}">${v}</button>`).join('');

// European wheel, real pocket order. The ball group (.bl) orbits; the wheel group (.wh) spins.
const WHEEL = [0, 32, 15, 19, 4, 21, 2, 25, 17, 34, 6, 27, 13, 36, 11, 30, 8, 23, 10, 5, 24, 16, 33, 1, 20, 14, 31, 9, 22, 18, 29, 7, 28, 12, 35, 3, 26];
function wheelSVG() {
  const st = 360 / 37, P = (r, a) => `${(100 + r * Math.sin(a * Math.PI / 180)).toFixed(2)},${(100 - r * Math.cos(a * Math.PI / 180)).toFixed(2)}`;
  const sec = WHEEL.map((n, i) => { const a0 = (i - 0.5) * st, a1 = (i + 0.5) * st, am = i * st, t = P(78, am).split(',');
    return `<path d="M${P(60, a0)} L${P(94, a0)} A94 94 0 0 1 ${P(94, a1)} L${P(60, a1)} A60 60 0 0 0 ${P(60, a0)}Z" fill="${n === 0 ? '#0a7d2c' : RED.has(n) ? '#c62828' : '#151515'}" stroke="#d4af37" stroke-width=".6"/><text x="${t[0]}" y="${t[1]}" fill="#fff" font-size="7" text-anchor="middle" dominant-baseline="central" transform="rotate(${am.toFixed(2)} ${t[0]} ${t[1]})">${n}</text>`; }).join('');
  return `<svg viewBox="0 0 200 200"><circle cx="100" cy="100" r="99" fill="#5a3a1a"/><circle cx="100" cy="100" r="96" fill="none" stroke="#d4af37" stroke-width="1"/><g class="wh">${sec}<circle cx="100" cy="100" r="58" fill="#8a6a3a" stroke="#d4af37"/><circle cx="100" cy="100" r="40" fill="#6b4a22" stroke="#d4af37" stroke-width=".6"/><circle cx="100" cy="100" r="12" fill="#d4af37"/><path d="M100 78V122M78 100H122" stroke="#d4af37" stroke-width="3"/></g><g class="bl"><circle class="bc" cx="100" cy="10" r="4.5" fill="#fff" stroke="#999"/></g></svg>`;
}
