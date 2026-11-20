// EP35 — wrong build #1 (the innocent prompt: "here's my gift card export — what's still out there?").
// Every bug intact, deliberately: floats, Date() rollovers, silent drops, clamped negatives,
// a vanished reload, and a dormancy judged against TODAY'S clock. DO NOT FIX — part of the episode.
(function (root) {
  function run(text) {
    const lines = String(text).trim().split(/\r?\n/).slice(1);
    const bal = {};      // card -> dollars (floats, oops)
    const last = {};     // card -> Date of last row seen
    let skipped = 0;
    for (const l of lines) {
      const [d, card, ev, v] = l.split(",");
      const dt = new Date(d);                       // 2025-02-29 rolls to Mar 1, oops
      const val = parseFloat(v);                    // "$25.00" -> NaN; "-40.00" -> -40
      if (!card || isNaN(dt.getTime()) || isNaN(val)) { skipped++; continue; }
      if (ev === "issue") bal[card] = (bal[card] || 0) + val;
      else if (ev === "redeem") bal[card] = (bal[card] || 0) - val;  // -(-40) ADDS, oops
      // "reload" and anything else: silently ignored, oops
      if (!last[card] || dt > last[card]) last[card] = dt;
    }
    let outstanding = 0, open = 0;
    for (const c in bal) {
      const b = Math.max(0, bal[c]);                // overdrafts clamped to zero and kept, oops
      bal[c] = b;
      if (b > 0.004) { outstanding += b; open++; }
    }
    // dormancy judged against the machine's clock — answers change by themselves, oops
    const today = new Date();
    let stale = 0, staleValue = 0;
    for (const c in bal) {
      if (bal[c] > 0.004 && (today - last[c]) / 86400000 >= 365) { stale++; staleValue += bal[c]; }
    }
    return {
      outstanding, openCards: open, cardsSeen: Object.keys(bal).length,
      stale, staleValue, skipped,
      verdict: "You are carrying $" + outstanding.toFixed(2) + " in open gift cards."
    };
  }
  root.GCLv1 = { run };
})(typeof window !== "undefined" ? window : globalThis);
