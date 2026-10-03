# Forecast extraction per frozen Protocol v1.1. Wind values are written to file only; never printed or summarized before the integrity checkpoint.
import requests, pygrib, numpy as np, datetime as dt, tempfile, os, email.utils, threading
S=requests.Session()
BASE={"gfs":"https://noaa-gfs-bdp-pds.s3.amazonaws.com","hrrr":"https://noaa-hrrr-bdp-pds.s3.amazonaws.com"}
def url(sys_,run,fh):
    d=run.strftime("%Y%m%d"); h=run.strftime("%H")
    return f"{BASE['gfs']}/gfs.{d}/{h}/atmos/gfs.t{h}z.pgrb2.0p25.f{fh:03d}" if sys_=="gfs" else f"{BASE['hrrr']}/hrrr.{d}/conus/hrrr.t{h}z.wrfsfcf{fh:02d}.grib2"
def pick_run(D):
    # latest 00Z/12Z run initialized at or before D-6h
    t=D-dt.timedelta(hours=6); r=t.replace(minute=0,second=0,microsecond=0)
    while r.hour not in (0,12) or r>t: r-=dt.timedelta(hours=1)
    return r
def hours_after(K):
    h0=K if (K.minute==0 and K.second==0) else (K.replace(minute=0,second=0)+dt.timedelta(hours=1))
    return [h0+dt.timedelta(hours=i) for i in range(4)]
GRID={}; GL=threading.Lock()
def fetch_uv(sys_,run,fh):
    u=url(sys_,run,fh)
    hi=S.head(u,timeout=60)
    if hi.status_code!=200: return None,"file missing"
    lm=email.utils.parsedate_to_datetime(hi.headers["Last-Modified"])
    idx=S.get(u+".idx",timeout=60)
    if idx.status_code!=200: return None,"idx missing"
    lines=idx.text.strip().split("\n"); rng={}
    for i,l in enumerate(lines):
        p=l.split(":")
        if p[3] in ("UGRD","VGRD") and p[4]=="10 m above ground":
            start=int(p[1]); end=int(lines[i+1].split(":")[1])-1 if i+1<len(lines) else None
            rng[p[3]]=(start,end)
    if set(rng)!={"UGRD","VGRD"}: return None,"10m U/V not in idx"
    out={}
    for var,(a,b) in rng.items():
        r=S.get(u,headers={"Range":f"bytes={a}-{'' if b is None else b}"},timeout=120)
        with tempfile.NamedTemporaryFile(suffix=".grb2",delete=False) as f: f.write(r.content); fn=f.name
        gf=pygrib.open(fn); g=gf.read(1)[0]; out[var]=g.values.astype("float32")
        with GL:
            if sys_ not in GRID: la,lo=g.latlons(); GRID[sys_]=(la,np.where(lo>180,lo-360,lo))
        gf.close(); del g; os.remove(fn)
    return dict(u=out["UGRD"],v=out["VGRD"],last_modified=lm,url=u),None
NC={}
def nearest(sys_,lat,lon):
    key=(sys_,round(lat,5),round(lon,5))
    if key in NC: return NC[key]
    NC[key]=_nearest(sys_,lat,lon); return NC[key]
def _nearest(sys_,lat,lon):
    la,lo=GRID[sys_]
    d=(np.radians(la-lat))**2+(np.cos(np.radians(lat))*np.radians(lo-lon))**2
    i=np.unravel_index(np.argmin(d),d.shape); return i,float(la[i]),float(lo[i])
