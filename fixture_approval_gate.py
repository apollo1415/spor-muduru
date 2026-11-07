#!/usr/bin/env python3
"""Fail-closed manual fixture approval gate. Evidence match alone never approves."""
import argparse,csv,json
from pathlib import Path
from odds_ev import utc_date
from coverage_audit import normalize

FIELDS=["event_id","provider_home","provider_away","league","home","away","kickoff_istanbul"]
def gate(queue,evidence,approvals):
    eligible=[];rejected=[];seen=set()
    evidence_index={(normalize(x["home"]),normalize(x["away"]),x["league"],utc_date(x["kickoff_utc"])):x for x in evidence}
    for a in approvals:
        eid=a.get("event_id","")
        candidates=[q for q in queue if q["event_id"]==eid]
        reason=None
        if eid in seen:reason="DUPLICATE_APPROVAL"
        elif a.get("decision")!="APPROVE":reason="NOT_EXPLICITLY_APPROVED"
        elif len(candidates)!=1:reason="NOT_UNIQUE_IN_REVIEW_QUEUE"
        else:
            q=candidates[0]
            expected={"provider_home":q["provider_home"],"provider_away":q["provider_away"],
                      "league":q["source_league"],"home":q["source_home"],"away":q["source_away"],
                      "kickoff_istanbul":q["source_kickoff_istanbul"]}
            if any(a.get(k)!=v for k,v in expected.items()):reason="APPROVAL_FIELDS_MISMATCH"
            elif q["league_review"]!="LEAGUE_MATCH" or q["review_status"]!="REVIEW_TIME_AND_LEAGUE":reason="REVIEW_NOT_UNIQUE_OR_LEAGUE_MISMATCH"
            elif float(q["delta_minutes"])>30:reason="KICKOFF_DELTA_TOO_LARGE"
            elif (normalize(q["provider_home"]),normalize(q["provider_away"]),q["provider_sport"],utc_date(q["provider_kickoff_utc"])) not in evidence_index:reason="NO_EXACT_ORGANIZER_EVIDENCE_SNAPSHOT"
        seen.add(eid)
        if reason:rejected.append({"event_id":eid,"reason":reason})
        else:eligible.append({k:(eid if k=="event_id" else expected[k]) for k in FIELDS})
    return eligible,rejected

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--queue",default="reports/odds/fixture_review_queue.csv")
    p.add_argument("--evidence",default="config/official_fixture_evidence.json")
    p.add_argument("--approvals",default="config/manual_fixture_approvals.csv")
    p.add_argument("--out",default="config/approved_fixture_mapping.csv")
    p.add_argument("--summary",default="reports/odds/approval_gate_summary.json")
    a=p.parse_args()
    with open(a.queue,encoding="utf-8-sig",newline="") as f:queue=list(csv.DictReader(f))
    evidence=json.loads(Path(a.evidence).read_text(encoding="utf-8"))["fixtures"]
    approvals=[]
    if Path(a.approvals).exists():
        with open(a.approvals,encoding="utf-8-sig",newline="") as f:approvals=list(csv.DictReader(f))
    eligible,rejected=gate(queue,evidence,approvals)
    out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True)
    with out.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(eligible)
    summary={"manual_approval_requests":len(approvals),"approved":len(eligible),"rejected":rejected,"status":"NO_MANUAL_APPROVALS" if not approvals else "GATE_EVALUATED"}
    target=Path(a.summary);target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"manual_approval_requests":len(approvals),"approved":len(eligible),"rejected":len(rejected),"status":summary["status"]},ensure_ascii=False))
if __name__=="__main__":main()
