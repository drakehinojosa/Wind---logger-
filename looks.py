"""Runs after grading. Computes statistics ONLY when a league's graded (non-void) count reaches an unlooked milestone.
Uses exactly the first N graded games by kickoff. Writes looks/<LG>_<N>.json. Nothing is computed between looks."""
import os, sys, json, math, collections
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from common import *
def stats(rows):
    n=len(rows); w=sum(r["result"]=="W" for r in rows); l=sum(r["result"]=="L" for r in rows); m=sum(r["units"] for r in rows)/n
    cl=collections.defaultdict(float)
    for r in rows: cl[r["date_et"]]+=r["units"]-m
    G=len(cl); se=math.sqrt(G/(G-1)*sum(v*v for v in cl.values()))/n if G>1 else float("nan")
    return dict(n=n,W=w,L=l,P=n-w-l,win_rate_ex_push=w/(w+l) if w+l else None,mean_unit_return=m,se_cr1_date=se,clusters=G,z=m/se if se and se==se and se>0 else None)
def main():
    ok,_=verify_chain("log/grades.jsonl"); assert ok,"grades chain broken"
    p=os.path.join(ROOT,"log/grades.jsonl")
    if not os.path.exists(p): print("no grades"); return
    G=[json.loads(l) for l in open(p) if json.loads(l)["status"]=="GRADED"]
    for lg in ("NFL","CFB"):
        rows=sorted([g for g in G if g["lg"]==lg],key=lambda g:(g["K"],g["event_id"]))
        prior=[json.load(open(os.path.join(ROOT,"looks",f))) for f in sorted(os.listdir(os.path.join(ROOT,"looks"))) if f.startswith(lg+"_")]
        if any(x["decision"] in ("PROMOTION GATE PASSED","KILL") for x in prior): continue
        for N in RULES["looks"]:
            if len(rows)<N or os.path.exists(os.path.join(ROOT,"looks",f"{lg}_{N}.json")): continue
            s=stats(rows[:N]); z=s["z"]; dec="CONTINUE"
            if z is not None and z>=RULES["promote"]["z_at_least"]: dec="PROMOTION GATE PASSED"
            elif N==150 and z is not None and z<=-1.28: dec="KILL"
            elif N in (300,450) and s["mean_unit_return"]<=0: dec="KILL"
            elif N==600: dec="KILL"
            json.dump(dict(league=lg,look=N,stats=s,decision=dec,computed_at=F(now())),open(os.path.join(ROOT,"looks",f"{lg}_{N}.json"),"w"),indent=1)
            print(f"LOOK {lg} {N}: {dec}")
            if dec in ("PROMOTION GATE PASSED","KILL"):
                open(os.path.join(ROOT,"looks",f"{lg}_STOPPED"),"w").write(f"{dec} at look {N}. Prospective testing stopped. Freeze files/code and return the full report for independent audit. No betting authorized.\n")
                break
if __name__=="__main__": main()
