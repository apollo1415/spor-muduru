#!/usr/bin/env python3
"""Human-readable fixture verification checklist; does not approve fixtures."""
import argparse,csv,json
from pathlib import Path
from collections import Counter
from odds_ev import utc_date
from coverage_audit import normalize

FIELDS=["event_id","provider_sport","provider_home","provider_away","provider_kickoff_utc","source_league","source_home","source_away","source_kickoff_istanbul","kickoff_delta_minutes","evidence_url","evidence_snapshot_match","independent_live_verification","manual_approval","blocking_reason"]
def checklist(queue,evidence):
    rows=[]
    for q in queue:
        matches=[e for e in evidence if
                 normalize(e.get("home",""))==normalize(q.get("provider_home","")) and
                 normalize(e.get("away",""))==normalize(q.get("provider_away","")) and
                 e.get("league")==q.get("provider_sport") and
                 utc_date(e["kickoff_utc"])==utc_date(q["provider_kickoff_utc"])]
        try:delta=float(q.get("delta_minutes",""))
        except (ValueError,TypeError):delta=float("inf")
        reasons=[]
        if q.get("review_status")!="REVIEW_TIME_AND_LEAGUE":reasons.append("AMBIGUOUS_IDENTITY")
        if q.get("league_review")!="LEAGUE_MATCH":reasons.append("LEAGUE_UNVERIFIED")
        if delta>30:reasons.append("KICKOFF_DISCREPANCY")
        if len(matches)!=1:reasons.append("EVIDENCE_MISSING_OR_AMBIGUOUS")
        reasons.append("INDEPENDENT_LIVE_VERIFICATION_REQUIRED")
        reasons.append("EXPLICIT_MANUAL_APPROVAL_REQUIRED")
        rows.append({"event_id":q.get("event_id",""),"provider_sport":q.get("provider_sport",""),
                     "provider_home":q.get("provider_home",""),"provider_away":q.get("provider_away",""),
                     "provider_kickoff_utc":q.get("provider_kickoff_utc",""),
                     "source_league":q.get("source_league",""),"source_home":q.get("source_home",""),
                     "source_away":q.get("source_away",""),"source_kickoff_istanbul":q.get("source_kickoff_istanbul",""),
                     "kickoff_delta_minutes":q.get("delta_minutes",""),"evidence_url":matches[0].get("source_url","") if len(matches)==1 else "",
                     "evidence_snapshot_match":"YES" if len(matches)==1 else "NO",
                     "independent_live_verification":"NOT_DONE","manual_approval":"NO",
                     "blocking_reason":";".join(reasons)})
    return rows

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--queue",default="reports/odds/fixture_review_queue.csv")
    p.add_argument("--evidence",default="config/official_fixture_evidence.json")
    p.add_argument("--out",default="reports/odds")
    a=p.parse_args()
    with open(a.queue,encoding="utf-8-sig",newline="") as f:queue=list(csv.DictReader(f))
    evidence=json.loads(Path(a.evidence).read_text(encoding="utf-8")).get("fixtures",[])
    rows=checklist(queue,evidence)
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    with (out/"fixture_verification_checklist.csv").open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(rows)
    summary={"candidates":len(rows),"snapshot_matches":sum(x["evidence_snapshot_match"]=="YES" for x in rows),
             "independently_verified":0,"approved":0,
             "warning":"Evidence URLs are historical/static references only. An operator must check current organizer fixture details and manually approve separately."}
    (out/"fixture_verification_checklist_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False))
if __name__=="__main__":main()
