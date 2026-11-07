#!/usr/bin/env python3
"""Discover candidate fixtures without automatically approving any odds joins."""
import argparse,csv,json,os,urllib.parse,urllib.request
from datetime import datetime,timezone
from difflib import SequenceMatcher
from pathlib import Path
from odds_ev import utc_date

COLUMNS=["event_id","provider_sport","provider_home","provider_away","provider_kickoff_utc","league","home","away","kickoff_istanbul","home_similarity","away_similarity","kickoff_delta_minutes","status"]
def score(a,b):
    return SequenceMatcher(None,a.casefold().strip(),b.casefold().strip()).ratio()
def candidates(matches,events,sport,minimum=.65,max_minutes=30):
    found=[]
    for e in events:
        try:
            t=utc_date(e["commence_time"])
            for m in matches:
                if m.get("decision")!="MODEL_ONLY_NO_ODDS":continue
                mt=utc_date(m["kickoff_istanbul"])
                delta=abs((t-mt).total_seconds())/60
                if delta>max_minutes:continue
                h=score(e["home_team"],m["home"]);a=score(e["away_team"],m["away"])
                if h<minimum or a<minimum:continue
                found.append({"event_id":e["id"],"provider_sport":sport,"provider_home":e["home_team"],
                              "provider_away":e["away_team"],"provider_kickoff_utc":e["commence_time"],
                              "league":m["league"],"home":m["home"],"away":m["away"],
                              "kickoff_istanbul":m["kickoff_istanbul"],"home_similarity":round(h,3),
                              "away_similarity":round(a,3),"kickoff_delta_minutes":round(delta,2),
                              "status":"REVIEW_REQUIRED_NOT_APPROVED"})
        except (KeyError,TypeError,ValueError):continue
    return sorted(found,key=lambda x:(x["event_id"],-min(x["home_similarity"],x["away_similarity"])))

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--matches",default="reports/today/matches.csv")
    p.add_argument("--out",default="reports/odds")
    p.add_argument("--sports",default="soccer_epl,soccer_uefa_champs_league,soccer_turkey_super_league")
    a=p.parse_args()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    with open(a.matches,encoding="utf-8-sig",newline="") as f:matches=list(csv.DictReader(f))
    key=os.environ.get("ODDS_API_KEY");results=[];statuses=[];all_events=[]
    if key:
        for sport in [s.strip() for s in a.sports.split(",") if s.strip()]:
            params=urllib.parse.urlencode({"apiKey":key,"regions":"eu","markets":"h2h","oddsFormat":"decimal"})
            url="https://api.the-odds-api.com/v4/sports/"+urllib.parse.quote(sport,safe="")+"/odds?"+params
            try:
                with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"spor-muduru-discovery/0.1"}),timeout=25) as resp:
                    events=json.load(resp)
                results.extend(candidates(matches,events,sport))
                all_events.extend({"sport_key":sport,"id":e.get("id"),"home_team":e.get("home_team"),"away_team":e.get("away_team"),"commence_time":e.get("commence_time")} for e in events)
                statuses.append({"sport":sport,"status":"FETCHED","events":len(events)})
            except Exception:
                # No exception text or URL: some HTTP errors include secret-bearing URLs.
                statuses.append({"sport":sport,"status":"FETCH_FAILED","events":0})
    (out/"provider_events.json").write_text(json.dumps(all_events,ensure_ascii=False),encoding="utf-8")
    with (out/"fixture_candidates.csv").open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=COLUMNS);w.writeheader();w.writerows(results)
    summary={"api_key_present":bool(key),"candidates":len(results),"sports":statuses,
             "approval":"NONE","warning":"Candidates are NOT approved. Manual review of identities, league, timezone and kickoff required. No odds are joined."}
    (out/"discovery_summary.json").write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding="utf-8")
    print(json.dumps({"api_key_present":bool(key),"candidates":len(results),"sports":statuses}))
if __name__=="__main__":main()
