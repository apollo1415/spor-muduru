#!/usr/bin/env python3
"""Optional The Odds API v4 ingestion; no fuzzy fixture joins and no secret logging."""
import argparse,csv,json,os,urllib.parse,urllib.request
from datetime import datetime,timezone
from pathlib import Path
from odds_ev import utc_date

FIELDS=["league","home","away","kickoff_istanbul","market","decimal_odds","source","captured_at_utc"]
def transform(events,mappings,captured):
    """Mapping keyed by provider event id; requires exact approved provider teams/time."""
    rows=[];issues=[]
    for e in events:
        eid=e.get("id")
        if eid not in mappings:continue
        m=mappings[eid]
        try:
            if e["home_team"]!=m["provider_home"] or e["away_team"]!=m["provider_away"]:
                raise ValueError("provider team mismatch")
            if utc_date(e["commence_time"])!=utc_date(m["kickoff_istanbul"]):
                raise ValueError("kickoff mismatch")
            if utc_date(captured)>=utc_date(e["commence_time"]):
                raise ValueError("event already started")
            for book in e.get("bookmakers",[]):
                updated=book.get("last_update")
                if not updated or utc_date(updated)>utc_date(captured):
                    continue
                if utc_date(updated)>=utc_date(e["commence_time"]):
                    continue
                for market in book.get("markets",[]):
                    for outcome in market.get("outcomes",[]):
                        mk=None
                        if market.get("key")=="h2h":
                            name=outcome.get("name")
                            if name==e["home_team"]:mk="home_win"
                            elif name==e["away_team"]:mk="away_win"
                            elif name=="Draw":mk="draw"
                        elif market.get("key")=="totals" and outcome.get("name")=="Over" and outcome.get("point")==2.5:
                            mk="over25"
                        if mk is None:continue
                        rows.append({"league":m["league"],"home":m["home"],"away":m["away"],
                                     "kickoff_istanbul":m["kickoff_istanbul"],"market":mk,
                                     "decimal_odds":outcome["price"],
                                     "source":"The Odds API v4 / "+str(book.get("key","unknown"))+" / event "+str(eid),
                                     "captured_at_utc":updated})
        except (KeyError,TypeError,ValueError) as ex:issues.append({"event_id":eid,"reason":str(ex)})
    return rows,issues

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--sport",default="soccer_epl",help="One supported provider sport key")
    p.add_argument("--regions",default="eu")
    p.add_argument("--mapping",default="config/approved_fixture_mapping.csv")
    p.add_argument("--out",default="reports/odds")
    a=p.parse_args()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    key=os.environ.get("ODDS_API_KEY")
    summary={"provider":"The Odds API v4","connected":bool(key),"approved_mapping_file":a.mapping,
             "rows":0,"issues":[],"status":"NO_API_KEY" if not key else "NOT_RUN"}
    rows=[]
    if key:
        if not Path(a.mapping).is_file():
            summary["status"]="NO_APPROVED_FIXTURE_MAPPING"
        else:
            with open(a.mapping,encoding="utf-8-sig",newline="") as f:
                maps=list(csv.DictReader(f))
            required={"event_id","provider_home","provider_away","league","home","away","kickoff_istanbul"}
            if not maps or any(not required.issubset(m) or any(not m[k].strip() for k in required) for m in maps):
                summary["status"]="INVALID_MAPPING"
            else:
                ids=[m["event_id"] for m in maps]
                if len(ids)!=len(set(ids)):raise ValueError("duplicate provider event id in mapping")
                params=urllib.parse.urlencode({"apiKey":key,"regions":a.regions,"markets":"h2h,totals","oddsFormat":"decimal","dateFormat":"iso"})
                url="https://api.the-odds-api.com/v4/sports/"+urllib.parse.quote(a.sport,safe="")+"/odds?"+params
                req=urllib.request.Request(url,headers={"User-Agent":"spor-muduru-research/0.8"})
                # Never print request URLs or API errors containing credentials.
                try:
                    with urllib.request.urlopen(req,timeout=25) as response:
                        events=json.load(response)
                    captured=datetime.now(timezone.utc).isoformat()
                    rows,issues=transform(events,{m["event_id"]:m for m in maps},captured)
                    summary.update(status="FETCHED",rows=len(rows),issues=issues[:30])
                except Exception:
                    summary["status"]="FETCH_FAILED"
    with (out/"verified_odds.csv").open("w",newline="",encoding="utf-8-sig") as f:
        w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(rows)
    (out/"provider_summary.json").write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding="utf-8")
    print(json.dumps({"provider":summary["provider"],"status":summary["status"],"rows":len(rows)}))
    if summary["status"]=="FETCH_FAILED":raise SystemExit(2)
if __name__=="__main__":main()
