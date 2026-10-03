"""Daily grader. Grades only LOGGED+qualified entries, 48h+ after kickoff, from the frozen score sources.
Appends to log/grades.jsonl (hash-chained). Prints counts only, never results."""
import os, sys, json, datetime as dt, pandas as pd
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from common import *
def unit(price,res): return 0.0 if res=="P" else -1.0 if res=="L" else (price/100 if price>0 else 100/abs(price))
def main():
    ok,n=verify_chain("log/entries.jsonl"); assert ok, f"entries chain broken at line {n}"
    E=[json.loads(l) for l in open(os.path.join(ROOT,"log/entries.jsonl"))] if os.path.exists(os.path.join(ROOT,"log/entries.jsonl")) else []
    done={json.loads(l)["event_id"] for l in open(os.path.join(ROOT,"log/grades.jsonl"))} if os.path.exists(os.path.join(ROOT,"log/grades.jsonl")) else set()
    todo=[e for e in E if e.get("status")=="LOGGED" and e.get("qualified") and e["event_id"] not in done and now()>P(e["K"])+dt.timedelta(hours=48)]
    if not todo: print("graded now: 0"); return
    seasons={P(e["K"]).year if P(e["K"]).month>=3 else P(e["K"]).year-1 for e in todo}
    nfl=pd.read_csv("https://github.com/nflverse/nfldata/raw/master/data/games.csv",usecols=["game_id","home_score","away_score"]).set_index("game_id")
    cfb=pd.concat([pd.read_csv(f"https://raw.githubusercontent.com/sportsdataverse/cfbfastR-data/main/schedules/csv/cfb_schedules_{y}.csv",usecols=["game_id","home_points","away_points"]) for y in seasons]).set_index("game_id")
    k=0
    for e in todo:
        tot=None
        if e["lg"]=="NFL" and e["ref_id"] in nfl.index and pd.notna(nfl.loc[e["ref_id"]].home_score): r=nfl.loc[e["ref_id"]]; tot=float(r.home_score+r.away_score)
        if e["lg"]=="CFB" and int(e["ref_id"]) in cfb.index and pd.notna(cfb.loc[int(e["ref_id"])].home_points): r=cfb.loc[int(e["ref_id"])]; tot=float(r.home_points+r.away_points)
        if tot is None:
            if now()>P(e["K"])+dt.timedelta(days=30): append_chained("log/grades.jsonl",dict(event_id=e["event_id"],lg=e["lg"],K=e["K"],status="VOID no official final score")); k+=1
            continue
        t=e["ticket"]; res="W" if tot<t["total"] else "L" if tot>t["total"] else "P"
        append_chained("log/grades.jsonl",dict(event_id=e["event_id"],lg=e["lg"],K=e["K"],date_et=P(e["K"]).astimezone(ET).date().isoformat(),status="GRADED",line=t["total"],price=t["under_price"],final_total=tot,result=res,units=unit(t["under_price"],res))); k+=1
    print("graded now:",k)   # counts only; no results printed
if __name__=="__main__": main()
