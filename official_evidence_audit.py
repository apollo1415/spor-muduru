#!/usr/bin/env python3
"""Compare review candidates to a manually curated organizer evidence snapshot; never approve."""
import argparse,csv,json
from pathlib import Path
from odds_ev import utc_date
from coverage_audit import normalize

def audit(rows,evidence):
    output=[]
    for r in rows:
        matches=[e for e in evidence if
                 normalize(e["home"])==normalize(r["provider_home"]) and
                 normalize(e["away"])==normalize(r["provider_away"]) and
                 e["league"]==r["provider_sport"] and
                 utc_date(e["kickoff_utc"])==utc_date(r["provider_kickoff_utc"])]
        unique=len(matches)==1
        output.append({"home":r["provider_home"],"away":r["provider_away"],
                       "provider_kickoff_utc":r["provider_kickoff_utc"],
                       "evidence_status":"OFFICIAL_FIXTURE_SNAPSHOT_MATCH" if unique else "MANUAL_REVIEW_REQUIRED",
                       "source_url":matches[0]["source_url"] if unique else "",
                       "approved":"NO"})
    return output

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--queue",default="reports/odds/fixture_review_queue.csv")
    p.add_argument("--evidence",default="config/official_fixture_evidence.json")
    p.add_argument("--out",default="reports/odds/official_evidence_audit.json")
    a=p.parse_args()
    with open(a.queue,encoding="utf-8-sig",newline="") as f:rows=list(csv.DictReader(f))
    evidence=json.loads(Path(a.evidence).read_text(encoding="utf-8"))["fixtures"]
    output=audit(rows,evidence)
    target=Path(a.out);target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps({"reviewed":len(output),"evidence_matches":sum(x["evidence_status"]=="OFFICIAL_FIXTURE_SNAPSHOT_MATCH" for x in output),"approved":0,"warning":"Static organizer evidence snapshot, not live validation or odds approval.","fixtures":output},ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"reviewed":len(output),"evidence_matches":sum(x["evidence_status"]=="OFFICIAL_FIXTURE_SNAPSHOT_MATCH" for x in output),"approved":0},ensure_ascii=False))
if __name__=="__main__":main()
