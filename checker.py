#!/usr/bin/env python3
"""The Gift Card Ledger — independent referee (EP35).
Implements RULES.md from scratch: integer cents / integer days, round-half-up.
Usage: checker.py giftcards.csv [--dormant-months 12] [--wave-days 60] [--crumb 1.00]
Prints a canonical JSON result for cross-implementation comparison.
"""
import sys, json, re, argparse
from datetime import date

def div_hu(num, den):
    if num < 0:
        return -div_hu(-num, den)
    return (2 * num + den) // (2 * den)

DATE_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
AMT_RE = re.compile(r"^(\d+)(?:\.(\d{1,2}))?$")
CARD_RE = re.compile(r"^[A-Za-z0-9-]{1,24}$")

def valid_date(s):
    m = DATE_RE.match(s)
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None

EPOCH = date(1970, 1, 1).toordinal()
def epoch_day(dt):
    return dt.toordinal() - EPOCH

def parse_amount(s):
    m = AMT_RE.match(s.strip())
    if not m:
        return None
    frac = m.group(2) or ""
    cents = int(m.group(1)) * 100 + (int((frac + "0")[:2]) if frac else 0)
    return cents if cents > 0 else None

def split_csv(text):
    lines = text.replace("\r", "").split("\n")
    while lines and lines[-1] == "":
        lines.pop()
    return [l.split(",") for l in lines]

def run(text, dormant_months=12, wave_days=60, crumb_dollars=1.00):
    dormant_days = dormant_months * 30
    crumb_cents = round(crumb_dollars * 100)
    refusals = []
    rows = split_csv(text)[1:]
    total = len(rows)
    events = []
    for i, f in enumerate(rows):
        row = i + 2
        if len(f) != 4:
            refusals.append({"row": row, "reason": "expected 4 fields"}); continue
        dt = valid_date(f[0].strip())
        if dt is None:
            refusals.append({"row": row, "reason": "bad date"}); continue
        card = f[1].strip()
        if not CARD_RE.match(card):
            refusals.append({"row": row, "reason": "bad card_id"}); continue
        ev = f[2].strip()
        if ev not in ("issue", "reload", "redeem"):
            refusals.append({"row": row, "reason": "unknown event"}); continue
        cents = parse_amount(f[3])
        if cents is None:
            refusals.append({"row": row, "reason": "unreadable amount"}); continue
        events.append({"row": row, "ed": epoch_day(dt), "y": dt.year, "mo": dt.month,
                       "card": card, "ev": ev, "cents": cents})
    refusals.sort(key=lambda r: r["row"])

    now_ed = max((e["ed"] for e in events), default=None)

    by_card = {}
    for e in events:
        by_card.setdefault(e["card"], []).append(e)
    flags, cards = [], []
    for cid, lst in by_card.items():
        lst.sort(key=lambda e: (e["ed"], e["row"]))
        flag = "opens-with-redeem" if lst[0]["ev"] == "redeem" else None
        bal = adds = subs = 0
        last_ed = None
        first_issue = None
        first_redeem_ed = None
        for e in lst:
            if e["ev"] == "redeem":
                bal -= e["cents"]; subs += e["cents"]
                if first_redeem_ed is None:
                    first_redeem_ed = e["ed"]
            else:
                bal += e["cents"]; adds += e["cents"]
                if e["ev"] == "issue" and first_issue is None:
                    first_issue = e
            if flag is None and bal < 0:
                flag = "overdrawn"
            if last_ed is None or e["ed"] > last_ed:
                last_ed = e["ed"]
        if flag:
            flags.append({"card": cid, "reason": flag}); continue
        cards.append({"id": cid, "list": lst, "bal": bal, "adds": adds, "subs": subs,
                      "last_ed": last_ed, "first_issue": first_issue,
                      "first_redeem_ed": first_redeem_ed})
    flags.sort(key=lambda f: f["card"])
    card_total = len(by_card)

    untrusted = (total > 0 and len(refusals) * 10 > total) or \
                (card_total > 0 and len(flags) * 10 > card_total)
    share = lambda n, t: div_hu(n * 1000, t) / 10 if t else 0

    open_cards = [c for c in cards if c["bal"] > 0]
    liability = sum(c["bal"] for c in open_cards)
    clean_ids = {c["id"] for c in cards}
    raw_adds = sum(e["cents"] for e in events if e["card"] in clean_ids and e["ev"] != "redeem")
    raw_subs = sum(e["cents"] for e in events if e["card"] in clean_ids and e["ev"] == "redeem")
    liability_by_types = raw_adds - raw_subs

    EDGES = [90, 180, 360, 720]
    aging = [0] * 5
    aging_n = [0] * 5
    for c in open_cards:
        age = now_ed - c["last_ed"]
        b = next((i for i, e in enumerate(EDGES) if age <= e), 4)
        aging[b] += c["bal"]; aging_n[b] += 1

    dorm = [c for c in open_cards if now_ed - c["last_ed"] >= dormant_days]
    dormant_cents = sum(c["bal"] for c in dorm)
    crumbs = [c for c in open_cards if c["bal"] <= crumb_cents]
    crumb_total = sum(c["bal"] for c in crumbs)
    dorm_list = sorted([c for c in dorm if c["bal"] > crumb_cents],
                       key=lambda c: (-c["bal"], c["id"]))
    dorm_list = [{"card": c["id"], "bal": c["bal"], "ageDays": now_ed - c["last_ed"]}
                 for c in dorm_list]

    holiday_value = redeemed_in_wave = holiday_cards = 0
    for c in cards:
        fi = c["first_issue"]
        if not fi or fi["mo"] not in (11, 12):
            continue
        holiday_cards += 1
        holiday_value += fi["cents"]
        got = sum(e["cents"] for e in c["list"]
                  if e["ev"] == "redeem" and e["ed"] <= fi["ed"] + wave_days)
        redeemed_in_wave += min(fi["cents"], got)
    wave_pct10 = div_hu(redeemed_in_wave * 1000, holiday_value) if holiday_value > 0 else None

    ds = sorted(c["first_redeem_ed"] - c["first_issue"]["ed"]
                for c in cards if c["first_redeem_ed"] is not None and c["first_issue"])
    median_days = None
    if ds:
        n = len(ds)
        median_days = ds[(n - 1) // 2] if n % 2 else div_hu(ds[n // 2 - 1] + ds[n // 2], 2)

    monthly = []
    if now_ed is not None:
        nd = date.fromordinal(now_ed + EPOCH)
        y, mo = nd.year, nd.month
        keys = []
        for _ in range(13):
            keys.insert(0, y * 100 + mo)
            mo -= 1
            if mo == 0:
                mo = 12; y -= 1
        agg = {k: {"issued": 0, "redeemed": 0} for k in keys}
        for c in cards:
            for e in c["list"]:
                k = e["y"] * 100 + e["mo"]
                if k not in agg:
                    continue
                if e["ev"] == "redeem":
                    agg[k]["redeemed"] += e["cents"]
                else:
                    agg[k]["issued"] += e["cents"]
        monthly = [{"ym": k, "issued": agg[k]["issued"], "redeemed": agg[k]["redeemed"]} for k in keys]

    dec_issued = all_issued = 0
    for c in cards:
        for e in c["list"]:
            if e["ev"] != "redeem":
                all_issued += e["cents"]
                if e["mo"] == 12:
                    dec_issued += e["cents"]
    dec_share10 = div_hu(dec_issued * 1000, all_issued) if all_issued > 0 else None

    oldest = None
    for c in open_cards:
        if c["bal"] > crumb_cents and (oldest is None or c["last_ed"] < oldest["last_ed"]):
            oldest = c

    aging_sum = sum(aging)
    re_bal = all(
        sum(e["cents"] for e in c["list"] if e["ev"] != "redeem")
        - sum(e["cents"] for e in c["list"] if e["ev"] == "redeem") == c["bal"]
        for c in cards)
    audits_pass = (liability == liability_by_types and aging_sum == liability and re_bal
                   and dormant_cents == sum(c["bal"] for c in dorm)
                   and dormant_cents <= liability and crumb_total <= liability
                   and not untrusted)

    return {
        "untrusted": untrusted or not audits_pass,
        "refusalRows": [r["row"] for r in refusals],
        "flags": flags,
        "shares": {"rows": share(len(refusals), total), "cards": share(len(flags), card_total)},
        "totals": {"liabilityCents": liability, "openCards": len(open_cards), "cleanCards": len(cards),
                   "dormantCents": dormant_cents, "dormantCards": len(dorm),
                   "crumbCents": crumb_total, "crumbCards": len(crumbs),
                   "holidayValue": holiday_value, "redeemedInWave": redeemed_in_wave,
                   "holidayCards": holiday_cards, "decIssued": dec_issued, "allIssued": all_issued},
        "aging": [{"bucket": i, "cents": aging[i], "cards": aging_n[i]} for i in range(5)],
        "dormList": dorm_list,
        "wavePct10": wave_pct10, "medianDays": median_days, "decShare10": dec_share10,
        "oldest": ({"card": oldest["id"], "bal": oldest["bal"], "ageDays": now_ed - oldest["last_ed"]}
                   if oldest else None),
        "monthly": monthly,
        "nowEd": now_ed,
        "rowCounts": {"rows": total, "cards": card_total},
    }

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--dormant-months", type=int, default=12)
    ap.add_argument("--wave-days", type=int, default=60)
    ap.add_argument("--crumb", type=float, default=1.00)
    a = ap.parse_args()
    res = run(open(a.file).read(), a.dormant_months, a.wave_days, a.crumb)
    print(json.dumps(res, sort_keys=True))
