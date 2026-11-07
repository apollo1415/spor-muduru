#!/usr/bin/env python3
"""Attach league-prior research availability to reviewed provider fixtures; never approve."""
import argparse,csv,json
from pathlib import Path
from collections import Counter

FIELDS=["event_id","provider_home","provider_away","source_league","kickoff_istanbul","standard_status","fallback_status","research_model","p_home","p_draw","p_away","eligible_for_odds","reason"]
def combine(review,fallbacks):
    index={}
    for f in fallbacks:
        key=(f.get("league"),f.get("home"),f.get("away"),f.get("kickoff_istanbul"))
        index.setdefault(key,[]).append(f)
    rows=[]
    for r in review:
        key=(r.get("source_league"),r.get("source_home"),r.get("source_away"),r.get("kickoff_istanbul"))
        matches=index.get(key,[])
        f=matches[0] if len(matches)==1 else {}
        standard=r.get("reason")=="MODEL_AVAILABLE_MANUAL_APPROVAL_REQUIRED"
        fallback=not standard and len(matches)==1 and f.get("baseline_status")=="LEAGUE_PRIOR_RESEARCH_ONLY"
        kind="STANDARD_RESEARCH" if standard else "LEAGUE_PRIOR_RESEARCH" if fallback else "NONE"
        result={"event_id":r.get("event_id",""),"provider_home":r.get("provider_home",""),"provider_away":r.get("provider_away",""),
                "source_league":r.get("source_league",""),"kickoff_istanbul":r.get("kickoff_istanbul",""),
                "standard_status":r.get("model_status",""),"fallback_status":f.get("baseline_status","NOT_AVAILABLE") if len(matches)<=1 else "DUPLICATE_FALLBACK",
                "research_model":kind,"eligible_for_odds":"NO","reason":"INDEPENDENT_FIXTURE_VERIFICATION_AND_MANUAL_APPROVAL_REQUIRED" if kind!="NONE" else r.get("reason","NO_MODEL")}
        for p in ("p_home","p_draw","p_away"):
            result[p]=r.get(p,"") if standard else f.get(p,"") if fallback else ""
        rows.append(result)
    return rows

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--review",default="reports/odds/forward_model_review.csv")
    p.add_argument("--fallback",default="reports/horizon/league_prior_fallback.csv")
    p.add_argument("--out",default="reports/odds")
    a=p.parse_args()
    def read(path):
        with open(path,encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
    rows=combine(read(a.review),read(a.fallback))
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    with (out/"combined_model_review.csv").open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(rows)
    summary={"reviewed":len(rows),"research_models":dict(Counter(r["research_model"] for r in rows)),"approved_for_odds":0,
             "warning":"Fallback probabilities are uncalibrated league priors, not betting recommendations; no automatic fixture approvals."}
    (out/"combined_model_review_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False))
if __name__=="__main__":main()
