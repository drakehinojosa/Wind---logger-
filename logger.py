"""Prospective logger, Protocol v1.1. Run every 10 minutes. Logs every eligible game at D, before kickoff.
Never reads scores. Writes log/entries.jsonl (append-only, hash-chained) and state/state.json."""
import os, sys, json, datetime as dt, requests, pandas as pd, math
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from common import *
import wx
KEY=os.environ["ODDS_API_KEY"]; API="https://api.the-odds-api.com/v4/sports"
T=RULES["timing"]; WIN=dt.timedelta(minutes=T["capture_window_min"])
def ref_schedules(season):
    c=f"state/ref_{season}.json"; s=load(c)
    if s and s.get("day")==now().date().isoformat(): return s
    nfl=pd.read_csv("https://github.com/nflverse/nfldata/raw/master/data/games.csv",usecols=["game_id","season","gameday","gametime","home_team","away_team"])
    nfl=nfl[nfl.season==season]
    cfb=pd.read_csv(f"https://raw.githubusercontent.com/sportsdataverse/cfbfastR-data/main/schedules/csv/cfb_schedules_{season}.csv",usecols=["game_id","start_date","home_team","away_team","home_division","away_division"])
    cfb=cfb[(cfb.home_division=="fbs")|(cfb.away_division=="fbs")]
    refs=[]
    for r in nfl.itertuples():
        t=dt.datetime.fromisoformat(f"{r.gameday}T{r.gametime}").replace(tzinfo=ET).astimezone(dt.timezone.utc)
        refs.append(dict(lg="NFL",ref_id=r.game_id,home=NAMES["nfl_abbr"][r.home_team],away=NAMES["nfl_abbr"][r.away_team],t=F(t)))
    for r in cfb.itertuples(): refs.append(dict(lg="CFB",ref_id=str(r.game_id),home=r.home_team,away=r.away_team,t=r.start_date.replace(".000Z","Z")))
    s=dict(day=now().date().isoformat(),refs=refs,cfb_names=sorted(set(cfb.home_team)|set(cfb.away_team),key=len,reverse=True)); save(c,s); return s
def cfb_name(o,names):
    if o in NAMES["cfb_alias"]: return NAMES["cfb_alias"][o]
    for n in names:
        if o==n or o.startswith(n+" "): return n
    return None
def match_ref(lg,home,away,commence,S):
    pair=frozenset((home,away)) if lg=="NFL" else frozenset((cfb_name(home,S["cfb_names"]),cfb_name(away,S["cfb_names"])))
    c=[r for r in S["refs"] if r["lg"]==lg and frozenset((r["home"],r["away"]))==pair and abs((P(r["t"])-P(commence)).total_seconds())<=4*86400]
    return c[0] if len(c)==1 else None
def espn_venue(lg,home,away,K):
    url=f"https://site.api.espn.com/apis/site/v2/sports/football/{'nfl' if lg=='NFL' else 'college-football'}/scoreboard"
    p=dict(dates=K.astimezone(ET).strftime("%Y%m%d"),limit=300)
    if lg=="CFB": p["groups"]=80
    for e in requests.get(url,params=p,timeout=60).json().get("events",[]):
        c=e["competitions"][0]; names={t["team"].get("displayName") for t in c["competitors"]}
        if {home,away}<=names or (home in names and away in names): return str(c.get("venue",{}).get("id"))
    return None
def forecast(K,D,lat,lon):
    run=wx.pick_run(D); out={}
    for s in ("gfs","hrrr"):
        sp=[]
        for h in wx.hours_after(K):
            fh=int((h-run).total_seconds()//3600); d,err=wx.fetch_uv(s,run,fh)
            if err: return None,f"{s} {err}",run
            if d["last_modified"]>D: return None,f"{s} Last-Modified after D",run
            i,la,lo=wx.nearest(s,lat,lon); sp.append(math.hypot(float(d["u"][i]),float(d["v"][i]))*2.23694)
        out[s]=dict(mph=sum(sp)/4,grid_lat=la,grid_lon=lo,url_first=d["url"])
    return out,None,run
def main():
    st=load("state/state.json",{"games":{}}); t0=now(); season=t0.year if t0.month>=3 else t0.year-1
    S=ref_schedules(season)
    for lg,cfg in RULES["leagues"].items():
        if os.path.exists(os.path.join(ROOT,"looks",f"{lg}_STOPPED")): continue   # terminal decision reached: testing stopped
        ev=requests.get(f"{API}/{cfg['sport_key']}/events",params=dict(apiKey=KEY),timeout=60).json()
        need_odds=False
        for e in ev:
            c=P(e["commence_time"]); g=st["games"].setdefault(e["id"],dict(lg=lg,home=e["home_team"],away=e["away_team"]))
            if g.get("final"): continue
            # anchor capture: latest listing seen at or before (listed commence - 36h)
            if c-dt.timedelta(hours=T["anchor_offset_h"])-WIN<=t0<=c-dt.timedelta(hours=T["anchor_offset_h"]):
                g["cand36"]=dict(commence=e["commence_time"],snap=F(t0))
            if "K" not in g and g.get("cand36") and t0>P(g["cand36"]["commence"])-dt.timedelta(hours=T["anchor_offset_h"]):
                g["K"]=g["cand36"]["commence"]
            if "K" not in g and not g.get("cand36") and t0>c-dt.timedelta(hours=T["anchor_offset_h"]):
                a=c-dt.timedelta(hours=T["anchor_offset_h"])
                ran=any(a-WIN<=P(h)<=a for h in st.get("heartbeats",[]))
                rec=dict(event_id=e["id"],lg=lg,home=e["home_team"],away=e["away_team"],listed_commence=e["commence_time"],
                         status="X1 not listed at K-36h (logger was running)" if ran else "ERROR no logger run in K-36h capture window")
                append_chained("log/entries.jsonl",rec); g["final"]=True; continue
            if "K" in g:
                D=P(g["K"])-dt.timedelta(hours=T["decision_offset_h"])
                if D-WIN<=t0<=D: g["candD"]=dict(commence=e["commence_time"],snap=F(t0)); need_odds=True
        if need_odds:
            od={x["id"]:x for x in requests.get(f"{API}/{cfg['sport_key']}/odds",params=dict(apiKey=KEY,regions="us",markets="totals",oddsFormat="american"),timeout=60).json()}
            for gid,g in st["games"].items():
                if g["lg"]==lg and g.get("candD") and g["candD"]["snap"]==F(t0) and gid in od:
                    q={}
                    for bk in od[gid]["bookmakers"]:
                        for mk in bk["markets"]:
                            if mk["key"]=="totals" and P(bk["last_update"])<=t0: q[bk["key"]]=dict(outcomes=mk["outcomes"],last_update=bk["last_update"])
                    g["oddsD"]=dict(snap=F(t0),quotes=q)
    # finalize games whose D has passed: write exactly one entry per game, before kickoff
    for gid,g in st["games"].items():
        if g.get("final") or "K" not in g: 
            if not g.get("final") and "cand36" not in g and g.get("seen_past_anchor"): pass
            continue
        K=P(g["K"]); D=K-dt.timedelta(hours=T["decision_offset_h"])
        if t0<=D: continue
        rec=dict(event_id=gid,lg=g["lg"],home=g["home"],away=g["away"],K=g["K"],D=F(D),anchor_snap=g["cand36"]["snap"])
        ref=match_ref(g["lg"],g["home"],g["away"],g["K"],S); rec["ref_id"]=ref["ref_id"] if ref else None
        if not ref: rec["status"]="X not on reference schedule (or out of scope)"
        elif not g.get("candD"): rec["status"]="ERROR missed D events capture"
        elif abs((P(g["candD"]["commence"])-K).total_seconds())>T["jitter_tolerance_min"]*60: rec["status"]="X4 kickoff changed >5 min by D"
        elif not g.get("oddsD"): rec["status"]="ERROR missed D odds capture"
        else:
            season_h=HIER.get(f"{g['lg']}|{season}"); ticket=None
            for i,(b,_) in enumerate(season_h["hierarchy"]):
                q=g["oddsD"]["quotes"].get(b)
                if q:
                    o={x["name"]:x for x in q["outcomes"]}
                    if "Under" in o and "Over" in o and o["Under"].get("point")==o["Over"].get("point"):
                        ticket=dict(book=b,rank=i+1,total=o["Under"]["point"],under_price=o["Under"]["price"],over_price=o["Over"]["price"],quote_last_update=q["last_update"],odds_snap=g["oddsD"]["snap"]); break
            vid=espn_venue(g["lg"],g["home"],g["away"],K); v=VEN.get(vid) if vid else None
            rec.update(ticket=ticket,venue_id=vid,venue=(v or {}).get("name"))
            if not ticket: rec["status"]="M2 no hierarchy book quoted at D"
            elif not v: rec["status"]="ERROR unknown venue (not in frozen table)"
            elif v["status"]!="OUTDOOR": rec["status"]=v["status"]
            else:
                fc,err,run=forecast(K,D,v["lat"],v["lon"]); rec["forecast_run"]=F(run)
                if err: rec["status"]="EXCL forecast "+err
                else:
                    cfg=RULES["leagues"][g["lg"]]; lo,hi=cfg["qualify_mph_min"],cfg["qualify_mph_max_exclusive"]
                    ok=all(fc[s]["mph"]>=lo and (hi is None or fc[s]["mph"]<hi) for s in ("gfs","hrrr"))
                    rec.update(forecast=fc,qualified=ok,status="LOGGED")
        if t0>=K: rec["status"]="ERROR finalized after kickoff: "+rec["status"]
        append_chained("log/entries.jsonl",rec); g["final"]=True
    st["heartbeats"]=[h for h in st.get("heartbeats",[]) if P(h)>t0-dt.timedelta(days=8)]+[F(t0)]
    save("state/state.json",st)
if __name__=="__main__": main()
