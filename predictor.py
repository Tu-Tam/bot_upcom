from collections import Counter
from datetime import datetime
import math
from database import get_results, get_full


MIN_HISTORY=10
SHORT_WINDOW=7; MEDIUM_WINDOW=30; LONG_WINDOW=90
WEIGHT_SHORT=0.30; WEIGHT_MEDIUM=0.25; WEIGHT_LONG=0.15; WEIGHT_WEEKDAY=0.15; WEIGHT_GAP=0.15


def norm_num(n): return str(n).zfill(2)
def parse_dt(s): return datetime.strptime(s,"%Y-%m-%d")


def extract_tails(rec):
    t = [rec["special"][-2:]]
    for g in [rec["g1"],rec["g2"],rec["g3"],rec["g4"],rec["g5"],rec["g6"],rec["g7"]]:
        for f in g:
            if isinstance(f,str) and len(f)>=2: t.append(f[-2:])
    if isinstance(rec.get("all"),dict): t.extend(rec["all"].get("tails2",[]))
    return [norm_num(x) for x in t if len(str(x))==2 or str(x).isdigit()]


def get_history_before(target_dt):
    tgt = parse_dt(target_dt)
    rows = get_results()
    hist=[]
    for d,*_ in sorted(rows,key=lambda r:r[0]):
        if parse_dt(d) < tgt:
            f=get_full(d)
            if f: hist.append(f)
    return sorted(hist, key=lambda x:x["date"], reverse=True)


def freq_window(hist, win):
    c=Counter()
    for r in hist[:win]: c.update(extract_tails(r))
    return {norm_num(i):c.get(norm_num(i),0) for i in range(100)}


def score_recency(hist, win):
    sc={norm_num(i):0.0 for i in range(100)}
    if not hist: return sc
    for idx,rec in enumerate(hist[:win]):
        w=math.exp(-idx/max(win/3,1))
        for tail in extract_tails(rec): sc[tail]+=w
    return sc


def norm_score(dic):
    if not dic: return dic
    vals=list(dic.values()); lo,hi=min(vals),max(vals)
    return {k: (v-lo)/(hi-lo) if hi!=lo else 0.0 for k,v in dic.items()}


def score_weekday(hist, target_dt):
    dow=parse_dt(target_dt).weekday()
    c=Counter()
    for rec in hist:
        if rec["weekday"]==dow: c.update(extract_tails(rec))
    raw={norm_num(i):c.get(norm_num(i),0) for i in range(100)}
    return norm_score(raw)


def score_gap(hist):
    sc={}
    for num in [norm_num(i) for i in range(100)]:
        g=len(hist)
        for idx,rec in enumerate(hist):
            if num in extract_tails(rec): g=idx; break
        sc[num]=math.log1p(g)
    return norm_score(sc)


def calculate(target_dt):
    hist=get_history_before(target_dt)
    if len(hist)<MIN_HISTORY: raise ValueError(f"Cần ít nhất {MIN_HISTORY} ngày lịch sử")
    sh=norm_score(score_recency(hist,SHORT_WINDOW))
    md=norm_score(score_recency(hist,MEDIUM_WINDOW))
    lg=norm_score(freq_window(hist,LONG_WINDOW))
    wd=score_weekday(hist,target_dt)
    gp=score_gap(hist)
    total={}
    for n in [norm_num(i) for i in range(100)]:
        total[n]=sh[n]*WEIGHT_SHORT + md[n]*WEIGHT_MEDIUM + lg[n]*WEIGHT_LONG + wd[n]*WEIGHT_WEEKDAY + gp[n]*WEIGHT_GAP
    return total


def predict(target_date, top_n=10):
    sc=calculate(target_date)
    rank=sorted(sc.items(), key=lambda kv: (-kv[1], kv[0]))
    return rank[:max(1,min(top_n,100))]
