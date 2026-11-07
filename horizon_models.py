#!/usr/bin/env python3
"""Forward-looking research models from the 14-day fixture inventory; no odds approval."""
import argparse,csv,json
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from spor_muduru import csvrows,model,IST
from odds_ev import utc_date

def build(fixtures,history_by_league,now):
    rows=[]
    for f in fixtures:
        try:
            kickoff=utc_date(f["kickoff_istanbul"])
            if kickoff<=now:continue
            lg=f["league"]
            history=history_by_league.get(lg,[])
            history=[r for r in history if r.get("date","")<now.astimezone(IST).date().isoformat()]
            result={"league":lg,"home":f["home"],"away":f["away"],"kickoff_istanbul":f["kickoff_istanbul"],
                    "source":"open-matchday","source_timezone_unverified":"YES"}
            result.update(model(f,history))
            rows.append(result)
        except (ValueError,KeyError,TypeError):continue
    return rows

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--fixtures",default="reports/odds/horizon_fixtures.json")
    p.add_argument("--out",default="reports/horizon")
    a=p.parse_args()
    fixtures=json.loads(Path(a.fixtures).read_text(encoding="utf-8"))
    leagues=sorted({f["league"] for f in fixtures})
    histories={};failures=[]
    for lg in leagues:
        try:
            histories[lg]=csvrows("data/"+lg+"/results_2627.csv")
        except Exception:failures.append(lg)
    from datetime import timezone
    now=datetime.now(timezone.utc)
    rows=build(fixtures,histories,now)
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    fields=sorted(set().union(*(r.keys() for r in rows))) if rows else ["league","home","away","kickoff_istanbul","decision"]
    with (out/"matches.csv").open("w",newline="",encoding="utf-8-sig") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
    summary={"future_fixtures":len(rows),"modelled":sum(r.get("decision")=="MODEL_ONLY_NO_ODDS" for r in rows),
             "history_leagues_failed":failures,"approved_odds":0,"recommendations":0,
             "warning":"Exploratory, uncalibrated future probabilities. Source kickoff timezone unverified; not eligible for automatic odds EV."}
    (out/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False))
if __name__=="__main__":main()
