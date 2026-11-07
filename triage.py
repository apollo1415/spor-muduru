#!/usr/bin/env python3
"""Conservative stability triage; NOT a betting or profitability ranking."""
import argparse,csv,json
from pathlib import Path

def classify(group,minimum_late=30,brier_tolerance=.02,logloss_tolerance=.05):
    if group.get("status")!="AUDITED":
        return "NO_EVIDENCE",group.get("status","UNKNOWN")
    if group.get("late_n",0)<minimum_late:
        return "NO_EVIDENCE","SMALL_LATE_SAMPLE"
    e=group["early"]["model"];l=group["late"]["model"]
    bd=l["brier"]-e["brier"];ld=l["log_loss"]-e["log_loss"]
    if bd>brier_tolerance or ld>logloss_tolerance:
        return "DETERIORATING","EARLY_LATE_METRICS_WORSENED"
    return "MONITOR","NO_LARGE_DETERIORATION_DETECTED"

def build(groups):
    rows=[]
    for key,g in groups.items():
        league,market=key.rsplit(" | ",1)
        status,reason=classify(g)
        e=g.get("early",{}).get("model",{})
        l=g.get("late",{}).get("model",{})
        rows.append({"league":league,"market":market,"triage":status,"reason":reason,
                     "n":g.get("n",0),"late_n":g.get("late_n",0),
                     "early_brier":e.get("brier"),"late_brier":l.get("brier"),
                     "early_log_loss":e.get("log_loss"),"late_log_loss":l.get("log_loss"),
                     "deployment":"RESEARCH_ONLY"})
    priority={"DETERIORATING":0,"MONITOR":1,"NO_EVIDENCE":2}
    return sorted(rows,key=lambda r:(priority[r["triage"]],r["market"],r["league"]))

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",default="reports/stability/summary.json")
    p.add_argument("--out",default="reports/triage")
    args=p.parse_args()
    source=json.loads(Path(args.input).read_text(encoding="utf-8"))
    rows=build(source["groups"])
    counts={s:sum(r["triage"]==s for r in rows) for s in ("DETERIORATING","MONITOR","NO_EVIDENCE")}
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    with (out/"market_triage.csv").open("w",newline="",encoding="utf-8-sig") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]) if rows else ["league","market","triage"]);w.writeheader();w.writerows(rows)
    summary={"counts":counts,"rules":{"min_late":30,"max_brier_increase":.02,"max_logloss_increase":.05},
             "warning":"Heuristic drift triage, NOT statistically significant evidence or a profitability ranking. Early/late changes can reflect league difficulty and sampling noise. No market approved for deployment.",
             "deployment":"RESEARCH_ONLY"}
    (out/"summary.json").write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False))
if __name__=="__main__":main()
