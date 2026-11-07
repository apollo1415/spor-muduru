#!/usr/bin/env python3
"""Research-only odds join: never invent odds, never place bets."""
import argparse,csv,json,math
from datetime import datetime,timezone
from pathlib import Path

MARKETS={"home_win":"p_home","draw":"p_draw","away_win":"p_away","over25":"p_over25","btts":"p_btts",
         "corners_over_9_5":"p_corners_over_9","shots_over_23_5":"p_shots_over_23",
         "target_over_7_5":"p_target_over_7","first_half_over_1_5":"p_first_half_goals_over_1",
         "first_half_corners_over_4_5":"p_first_half_corners_over_4"}
REQUIRED={"league","home","away","kickoff_istanbul","market","decimal_odds","source","captured_at_utc"}

def utc_date(s):
    d=datetime.fromisoformat(s.replace("Z","+00:00"))
    if d.tzinfo is None:raise ValueError("timezone required")
    return d.astimezone(timezone.utc)

def key(r,market):
    return (r["league"].strip(),r["home"].strip(),r["away"].strip(),r["kickoff_istanbul"].strip(),market)

def evaluate(matches,odds):
    match_index={}
    for m in matches:
        if m.get("decision")!="MODEL_ONLY_NO_ODDS":continue
        for market,pkey in MARKETS.items():
            if m.get(pkey) not in ("",None):
                k=key(m,market)
                if k in match_index:raise ValueError("ambiguous duplicate fixture: "+str(k))
                match_index[k]=(m,pkey)
    output=[];rejected=[];seen=set()
    for o in odds:
        try:
            if not REQUIRED.issubset(o):raise ValueError("missing required columns")
            market=o["market"].strip()
            if market not in MARKETS:raise ValueError("unsupported market")
            k=key(o,market)
            if k in seen:raise ValueError("duplicate odds key")
            seen.add(k)
            if k not in match_index:raise ValueError("no exact eligible fixture match")
            m,pkey=match_index[k]
            price=float(o["decimal_odds"])
            p=float(m[pkey])
            if not math.isfinite(price) or price<=1:raise ValueError("invalid decimal odds")
            if not math.isfinite(p) or not 0<=p<=1:raise ValueError("invalid model probability")
            captured=utc_date(o["captured_at_utc"])
            kickoff=utc_date(o["kickoff_istanbul"])
            if captured>=kickoff:raise ValueError("odds captured at or after kickoff")
            if not o["source"].strip():raise ValueError("empty source")
            output.append({"league":k[0],"home":k[1],"away":k[2],"kickoff_istanbul":k[3],
                           "market":market,"model_probability":round(p,5),
                           "decimal_odds":price,"implied_probability":round(1/price,5),
                           "theoretical_ev":round(p*price-1,5),"source":o["source"],
                           "captured_at_utc":o["captured_at_utc"],"status":"RESEARCH_ONLY_NOT_VALIDATED"})
        except (KeyError,TypeError,ValueError) as e:
            rejected.append({"row":len(output)+len(rejected)+1,"reason":str(e)})
    return output,rejected

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--matches",default="reports/today/matches.csv")
    ap.add_argument("--odds",default=None,help="Optional verified timestamped odds CSV; absent means zero EV rows")
    ap.add_argument("--out",default="reports/odds")
    args=ap.parse_args()
    with open(args.matches,encoding="utf-8-sig",newline="") as f:matches=list(csv.DictReader(f))
    odds=[]
    if args.odds:
        with open(args.odds,encoding="utf-8-sig",newline="") as f:odds=list(csv.DictReader(f))
    result,rejected=evaluate(matches,odds)
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    fields=["league","home","away","kickoff_istanbul","market","model_probability","decimal_odds","implied_probability","theoretical_ev","source","captured_at_utc","status"]
    with (out/"research_ev.csv").open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(result)
    summary={"odds_source_connected":bool(args.odds),"odds_rows":len(odds),"matched":len(result),"rejected":len(rejected),
             "rejections":rejected[:50],"recommendations":0,"status":"RESEARCH_ONLY",
             "warning":"No verified live odds feed by default. Theoretical EV assumes unvalidated probabilities and ignores fees/limits; no betting advice."}
    (out/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({k:v for k,v in summary.items() if k!="rejections"},ensure_ascii=False))
if __name__=="__main__":main()
