#!/usr/bin/env python3
"""Audit forward model availability for exact provider fixture review candidates; no odds approval."""
import argparse,csv,json
from pathlib import Path
from collections import Counter
from odds_ev import utc_date

FIELDS=["event_id","provider_sport","provider_home","provider_away","source_league","source_home","source_away","kickoff_istanbul","delta_minutes","league_review","review_status","model_status","p_home","p_draw","p_away","p_over25","p_btts","eligible_for_odds","reason"]
def reconcile(queue,models):
    index={}
    for m in models:
        key=(m.get("league"),m.get("home"),m.get("away"),m.get("kickoff_istanbul"))
        index.setdefault(key,[]).append(m)
    out=[]
    for q in queue:
        key=(q.get("source_league"),q.get("source_home"),q.get("source_away"),q.get("source_kickoff_istanbul"))
        candidates=index.get(key,[])
        m=candidates[0] if len(candidates)==1 else {}
        reason=("DUPLICATE_MODEL" if len(candidates)>1 else
                "NO_EXACT_FORWARD_MODEL" if not m else
                "INSUFFICIENT_MODEL_HISTORY" if m.get("decision")!="MODEL_ONLY_NO_ODDS" else
                "LEAGUE_OR_IDENTITY_REVIEW_REQUIRED" if q.get("league_review")!="LEAGUE_MATCH" or q.get("review_status")!="REVIEW_TIME_AND_LEAGUE" else
                "KICKOFF_REVIEW_REQUIRED" if float(q.get("delta_minutes") or 1e9)>30 else
                "MODEL_AVAILABLE_MANUAL_APPROVAL_REQUIRED")
        row={"event_id":q.get("event_id",""),"provider_sport":q.get("provider_sport",""),
             "provider_home":q.get("provider_home",""),"provider_away":q.get("provider_away",""),
             "source_league":q.get("source_league",""),"source_home":q.get("source_home",""),"source_away":q.get("source_away",""),"kickoff_istanbul":q.get("source_kickoff_istanbul",""),
             "delta_minutes":q.get("delta_minutes",""),"league_review":q.get("league_review",""),
             "review_status":q.get("review_status",""),"model_status":m.get("decision","NOT_AVAILABLE"),
             "eligible_for_odds":"NO","reason":reason}
        for p in ("p_home","p_draw","p_away","p_over25","p_btts"):
            row[p]=m.get(p,"") if reason=="MODEL_AVAILABLE_MANUAL_APPROVAL_REQUIRED" else ""
        out.append(row)
    return out
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--queue",default="reports/odds/fixture_review_queue.csv")
    p.add_argument("--models",default="reports/horizon/matches.csv")
    p.add_argument("--out",default="reports/odds")
    a=p.parse_args()
    with open(a.queue,encoding="utf-8-sig",newline="") as f:queue=list(csv.DictReader(f))
    with open(a.models,encoding="utf-8-sig",newline="") as f:models=list(csv.DictReader(f))
    rows=reconcile(queue,models)
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    with (out/"forward_model_review.csv").open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(rows)
    summary={"reviewed":len(rows),"forward_model_available":sum(x["reason"]=="MODEL_AVAILABLE_MANUAL_APPROVAL_REQUIRED" for x in rows),
             "reasons":dict(Counter(x["reason"] for x in rows)),"odds_approved":0,
             "warning":"Model availability is not fixture approval, independent kickoff verification, or calibrated EV."}
    (out/"forward_model_review_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False))
if __name__=="__main__":main()
