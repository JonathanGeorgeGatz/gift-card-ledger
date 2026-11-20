// EP35 — wrong build #2 (the rules prompt, rebuilt). Looks housebroken; still wrong in four ways,
// all real output of the second session: redeems processed first on a tied date, dormancy aged
// from the first issue instead of the last visit, the wave read as "redeemed in January" (the
// window dial changes nothing), and flagged cards clamped and KEPT in the headline.
// DO NOT FIX — this file is part of the episode.
(function (root) {
  const divHU = (num, den) => num >= 0 ? Math.floor((2 * num + den) / (2 * den)) : -Math.floor((2 * (-num) + den) / (2 * den));
  const MONTH_DAYS = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  function validDate(s) {
    const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s); if (!m) return null;
    const y = +m[1], mo = +m[2], d = +m[3];
    if (mo < 1 || mo > 12 || d < 1) return null;
    let dim = MONTH_DAYS[mo - 1];
    if (mo === 2 && ((y % 4 === 0 && y % 100 !== 0) || y % 400 === 0)) dim = 29;
    if (d > dim) return null;
    return { y, mo, d };
  }
  function epochDay(y, mo, d) {
    y -= mo <= 2 ? 1 : 0;
    const era = Math.floor((y >= 0 ? y : y - 399) / 400);
    const yoe = y - era * 400;
    const doy = Math.floor((153 * (mo + (mo > 2 ? -3 : 9)) + 2) / 5) + d - 1;
    return era * 146097 + yoe * 365 + Math.floor(yoe / 4) - Math.floor(yoe / 100) + doy - 719468;
  }
  function parseAmount(s) {
    const m = /^(\d+)(?:\.(\d{1,2}))?$/.exec(String(s).trim()); if (!m) return null;
    const c = +m[1] * 100 + (m[2] ? +((m[2] + "0").slice(0, 2)) : 0);
    return c > 0 ? c : null;
  }
  const CARD_RE = /^[A-Za-z0-9-]{1,24}$/;
  function run(text, dials) {
    const dormantDays = (((dials && dials.dormantMonths) || 12)) * 30;
    const crumbCents = Math.round((((dials && dials.crumbDollars) || 1.00)) * 100);
    const refusals = [];
    const rows = String(text).replace(/\r/g, "").split("\n").slice(1).filter(x => x !== "").map(l => l.split(","));
    const events = [];
    rows.forEach((f, i) => {
      const row = i + 2;
      if (f.length !== 4) { refusals.push(row); return; }
      const dt = validDate(f[0].trim()); if (!dt) { refusals.push(row); return; }
      const card = f[1].trim(); if (!CARD_RE.test(card)) { refusals.push(row); return; }
      const ev = f[2].trim(); if (ev !== "issue" && ev !== "reload" && ev !== "redeem") { refusals.push(row); return; }
      const cents = parseAmount(f[3]); if (cents === null) { refusals.push(row); return; }
      events.push({ row, ed: epochDay(dt.y, dt.mo, dt.d), y: dt.y, mo: dt.mo, card, ev, cents });
    });
    let nowEd = null;
    for (const e of events) if (nowEd === null || e.ed > nowEd) nowEd = e.ed;
    const byCard = new Map();
    for (const e of events) { if (!byCard.has(e.card)) byCard.set(e.card, []); byCard.get(e.card).push(e); }
    const flags = [];
    const cards = [];
    for (const [id, list] of byCard.entries()) {
      // "process spends before loads, to be conservative" — redeems first on a tied date, oops
      list.sort((a, b) => a.ed - b.ed || (a.ev === "redeem" ? -1 : 1) - (b.ev === "redeem" ? -1 : 1));
      let bal = 0, flagged = null, lastEd = -Infinity, firstIssue = null;
      for (const e of list) {
        if (e.ev === "redeem") bal -= e.cents; else { bal += e.cents; if (e.ev === "issue" && !firstIssue) firstIssue = e; }
        if (bal < 0) { flagged = flagged || "overdrawn"; bal = 0; }   // clamped and KEPT, oops
        if (e.ed > lastEd) lastEd = e.ed;
      }
      if (flagged) flags.push({ card: id, reason: flagged });
      cards.push({ id, list, bal, lastEd, firstIssue });              // flagged cards stay in, oops
    }
    const open = cards.filter(c => c.bal > 0);
    // crumbs declared noise and dropped from the headline, oops
    const liabilityCents = open.filter(c => c.bal > crumbCents).reduce((a, c) => a + c.bal, 0);
    // dormancy aged from the FIRST ISSUE, not the last visit, oops
    const dorm = open.filter(c => c.firstIssue && nowEd - c.firstIssue.ed >= dormantDays);
    const dormantCents = dorm.reduce((a, c) => a + c.bal, 0);
    // the wave: "how much came back in January" — a different question; the dial is dead, oops
    let holidayValue = 0, redeemedInWave = 0;
    for (const c of cards) {
      const fi = c.firstIssue;
      if (!fi || (fi.mo !== 11 && fi.mo !== 12)) continue;
      holidayValue += fi.cents;
      let got = 0;
      for (const e of c.list) if (e.ev === "redeem" && e.mo === 1) got += e.cents;
      redeemedInWave += Math.min(fi.cents, got);
    }
    const wavePct10 = holidayValue > 0 ? divHU(redeemedInWave * 1000, holidayValue) : null;
    return {
      refusals, flags,
      totals: { liabilityCents, openCards: open.length, dormantCents, dormantCards: dorm.length,
                holidayValue, redeemedInWave },
      wavePct10, nowEd
    };
  }
  root.GCLv2 = { run };
})(typeof window !== "undefined" ? window : globalThis);
