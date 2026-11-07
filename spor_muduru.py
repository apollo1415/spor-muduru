#!/usr/bin/env python3
"""SPOR MUDURU — free source inventory; transparent, uncalibrated Poisson baseline."""
import argparse,csv,io,json,math,re,urllib.request
from datetime import datetime,timedelta,timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT="https://raw.githubusercontent.com/oladeeayo/open-matchday/master/"
IST=ZoneInfo("Europe/Istanbul")
def get(path):
    req=urllib.request.Request(ROOT+path,headers={"User-Agent":"spor-muduru-personal-research/0.2"})
    with urllib.request.urlopen(req,timeout=25) as r:return r.read().decode("utf-8-sig")
def csvrows(path):return list(csv.DictReader(io.StringIO(get(path))))
def value(x):
    try:return float(x) if x not in ("",None) else None
    except (ValueError,TypeError):return None
def average(v):return sum(v)/len(v) if v else None
def sample(rows,team,home,field):
    key="home" if home else "away"
    return [v for r in reversed(rows) if r.get(key)==team if (v:=value(r.get(field))) is not None][:10]
def poisson(lh,la):
    n=25
    p=lambda l,i:math.exp(-l+i*math.log(l)-math.lgamma(i+1))
    h=[p(lh,i) for i in range(n)];a=[p(la,i) for i in range(n)]
    z={"p_home":0.,"p_draw":0.,"p_away":0.,"p_over25":0.,"p_btts":0.}
    for i in range(n):
        for j in range(n):
            x=h[i]*a[j]
            z["p_home" if i>j else "p_draw" if i==j else "p_away"]+=x
            if i+j>=3:z["p_over25"]+=x
            if i>0 and j>0:z["p_btts"]+=x
    return {k:round(v,5) for k,v in z.items()}
def model(f,history):
    h,a=f["home"],f["away"]
    hf=sample(history,h,True,"ft_home");ha=sample(history,h,True,"ft_away")
    af=sample(history,a,False,"ft_away");aa=sample(history,a,False,"ft_home")
    z={"n_home":len(hf),"n_away":len(af),"decision":"INSUFFICIENT_HISTORY"}
    if min(map(len,[hf,ha,af,aa]))<5:return z
    league_h=[v for r in history if (v:=value(r.get("ft_home"))) is not None]
    league_a=[v for r in history if (v:=value(r.get("ft_away"))) is not None]
    if not league_h or not league_a:return z
    lh=max(.15,min(5.,.8*(average(hf)+average(aa))/2+.2*average(league_h)))
    la=max(.15,min(5.,.8*(average(af)+average(ha))/2+.2*average(league_a)))
    z.update(decision="MODEL_ONLY_NO_ODDS",lambda_home=round(lh,3),lambda_away=round(la,3))
    z.update(poisson(lh,la))
    for name,home,fields in [
        ("home",True,["home_corners","home_shots","home_target","home_corners_1h","ht_home"]),
        ("away",False,["away_corners","away_shots","away_target","away_corners_1h","ht_away"])]:
        team=h if home else a
        for field in fields:
            v=sample(history,team,home,field)
            z["n_"+name+"_"+field]=len(v)
            z["avg_"+name+"_"+field]=round(average(v),2) if len(v)>=5 else None
    return z
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--date",default=datetime.now(IST).date().isoformat())
    ap.add_argument("--out",default="reports/today")
    ap.add_argument("--as-of",default=None)
    args=ap.parse_args()
    now=datetime.fromisoformat(args.as_of).astimezone(IST) if args.as_of else datetime.now(IST)
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    index=get("LEAGUE_INDEX.md")
    leagues=list(dict.fromkeys(re.findall(r'^\|\s*`([^`]+)`\s*\|',index,re.M)))
    # Match fixtures in source UTC date and adjacent UTC dates to cover Istanbul day boundaries.
    dates={(datetime.fromisoformat(args.date).date()+timedelta(days=d)).isoformat() for d in [-1,0,1]}
    matches=[];coverage=[];errors=[]
    for lg in leagues:
        try:
            folder=f"data/{lg}/"
            fixtures=csvrows(folder+"fixtures_2627.csv")
            results=csvrows(folder+"results_2627.csv")
            history=[r for r in results if r.get("date","")<args.date]
            history.sort(key=lambda r:(r.get("date",""),r.get("time","")))
            found=0
            for f in fixtures:
                if f.get("date") not in dates:continue
                record={"league":lg,"home":f.get("home"),"away":f.get("away"),"source_date":f.get("date"),"source_time":f.get("time")}
                try:
                    # Source specifies a fixed UTC+1 clock convention, NOT daylight-saving CET.
                    dt=datetime.strptime(f["date"]+" "+f["time"],"%Y-%m-%d %H:%M").replace(tzinfo=timezone(timedelta(hours=1))).astimezone(IST)
                    record["kickoff_istanbul"]=dt.isoformat()
                    if dt.date().isoformat()!=args.date:continue
                    found+=1
                    if dt<=now:record["decision"]="STARTED_OR_PAST"
                    else:record.update(model(f,history))
                except (ValueError,TypeError,KeyError):
                    if f.get("date")!=args.date:continue
                    found+=1;record["decision"]="UNKNOWN_KICKOFF"
                matches.append(record)
            coverage.append({"league":lg,"fixtures":len(fixtures),"history":len(history),"today":found,"status":"OK"})
        except Exception as exc:
            errors.append({"league":lg,"error":str(exc)[:250]})
            coverage.append({"league":lg,"fixtures":0,"history":0,"today":0,"status":"ERROR"})
    def write_csv(name,items):
        keys=sorted(set().union(*(r.keys() for r in items))) if items else ["league","status"]
        with (out/name).open("w",newline="",encoding="utf-8-sig") as f:
            w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(items)
    write_csv("matches.csv",matches);write_csv("coverage.csv",coverage)
    summary={"date":args.date,"as_of":now.isoformat(),"source":"oladeeayo/open-matchday","leagues_attempted":len(leagues),"leagues_ok":len(leagues)-len(errors),"leagues_failed":len(errors),"matches_total":len(matches),"matches_future":sum(r.get("decision") not in ("STARTED_OR_PAST","UNKNOWN_KICKOFF") for r in matches),"matches_modelled":sum(r.get("decision")=="MODEL_ONLY_NO_ODDS" for r in matches),"bet_recommendations":0,"errors":errors,"limitations":["Not the full official Iddaa coupon","No verified odds, EV, xG or lineups","Poisson baseline not backtested or calibrated","Source kickoff timezone may be inaccurate; verify official schedules","No independent corner/shot/half-time probabilistic models"]}
    (out/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False))
    if not leagues or len(errors)==len(leagues):raise SystemExit(2)
if __name__=="__main__":main()
