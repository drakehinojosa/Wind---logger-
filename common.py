import json, os, hashlib, datetime as dt, zoneinfo, requests
ROOT=os.path.dirname(os.path.abspath(__file__)); ET=zoneinfo.ZoneInfo("America/New_York")
P=lambda s:dt.datetime.fromisoformat(s.replace("Z","+00:00")); F=lambda d:d.strftime("%Y-%m-%dT%H:%M:%SZ")
def now(): return dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
def load(p,default=None):
    p=os.path.join(ROOT,p); return json.load(open(p)) if os.path.exists(p) else default
def save(p,obj): json.dump(obj,open(os.path.join(ROOT,p),"w"),indent=1)
def append_chained(p,rec):
    """Append-only JSONL with a SHA-256 hash chain: each line stores the hash of the previous line."""
    p=os.path.join(ROOT,p); prev="GENESIS"
    if os.path.exists(p):
        lines=open(p).read().strip().split("\n")
        if lines and lines[0]: prev=hashlib.sha256(lines[-1].encode()).hexdigest()
    rec=dict(rec,prev_hash=prev,logged_at=F(now()))
    with open(p,"a") as f: f.write(json.dumps(rec,sort_keys=True)+"\n")
def verify_chain(p):
    p=os.path.join(ROOT,p)
    if not os.path.exists(p): return True,0
    prev="GENESIS"; n=0
    for line in open(p):
        line=line.rstrip("\n")
        if not line: continue
        if json.loads(line)["prev_hash"]!=prev: return False,n
        prev=hashlib.sha256(line.encode()).hexdigest(); n+=1
    return True,n
RULES=load("frozen/rules.json"); HIER=load("frozen/book_hierarchies.json"); VEN=load("frozen/venues.json"); NAMES=load("frozen/names.json")
