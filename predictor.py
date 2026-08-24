from collections import Counter
from datetime import datetime
import math

from database import get_results, get_full


MIN_HISTORY = 10
SHORT_WINDOW=7; MEDIUM_WINDOW=30; LONG_WINDOW=90
WEIGHT_SHORT=0.30; WEIGHT_MEDIUM=0.25; WEIGHT_LONG=0.15; WEIGHT_WEEKDAY=0.15; WEIGHT_GAP=0.15


def normalize_number(n): return str(n).zfill(2)
def parse_date(s): return datetime.strptime(s,"%Y-%m-%d")


def extract_all_tails(rec):
    tails = [rec["special"][-2:]]
    for g in ["g1","g2","g3","g4","g5","g6","g7"]:
        for num5 in rec.get(g,[]):
            if isinstance(num5,str) and len(num5)>=2: tails.append(num5[-2:])
    if isinstance(rec.get("all"),dict): tails.extend(rec["all"].get("tails2",[]))
    return [normalize_number(t) for t in tails if len(str(t))==2 or str(t).isdigit()]


def get_full_history_before(target_date):
    target_dt=parse_date(target_date)
    rows=get_results()
    hist=[]
    for dt_str, *_ in sorted(rows, key=lambda r:r[0]):
        if parse_date(dt_str) < target_dt:
            f=get_full(dt_str)
            if f: hist.append(f)
    return sorted(hist, key=lambda r:r["date"], reverse=True)


def build_frequency(hist, win):
    c=Counter()
    for r in hist[:win]: c.update(extract_all_tails(r))
    return {normalize_number(i):c.get(normalize_number(i),0) for i in range(100)}


def recency_score(hist, win):
    sc={normalize_number(i):0.0 for i in range(100)}
    if not hist: return sc
    for idx,rec in enumerate(hist[:win]):
        w=math.exp(-idx/max(win/3,1))
        for t in extract_all_tails(rec): sc[t]+=w
    return sc


def normalize_scores(dic):
    if not dic: return dic
    vals=list(dic.values()); lo,hi=min(vals),max(vals)
    return {k: (v-lo)/(hi-lo) if hi!=lo else 0.0 for k,v in dic.items()}


def weekday_score(hist, target_dt_str):
    dow=parse_date(target_dt_str).weekday()
    c=Counter()
    for rec in hist:
        if rec["weekday"]==dow: c.update(extract_all_tails(rec))
    raw={normalize_number(i):c.get(normalize_number(i),0) for i in range(100)}
    return normalize_scores(raw)


def gap_score(hist):
    sc={}
    all_n=[normalize_number(i) for i in range(100)]
    for n in all_n:
        g=len(hist)
        for idx,rec in enumerate(hist):
            if n in extract_all_tails(rec): g=idx; break
        sc[n]=math.log1p(g)
    return normalize_scores(sc)


def calculate_scores(target_date):
    hist=get_full_history_before(target_date)
    if not hist: raise ValueError("❌ Chưa có lịch sử! Cập nhật trước.")
    if len(hist)<MIN_HISTORY: raise ValueError(f"⚠️ Cần ít nhất {MIN_HISTORY} ngày.")

    sh=normalize_scores(recency_score(hist,SHORT_WINDOW))
    md=normalize_scores(recency_score(hist,MEDIUM_WINDOW))
    lg=normalize_scores(build_frequency(hist,LONG_WINDOW))
    wd=weekday_score(hist,target_date)
    gp=gap_score(hist)

    total={}
    for num in [normalize_number(i) for i in range(100)]:
        total[num]=sh[num]*WEIGHT_SHORT + md[num]*WEIGHT_MEDIUM + lg[num]*WEIGHT_LONG + wd[num]*WEIGHT_WEEKDAY + gp[num]*WEIGHT_GAP
    return total


def predict(target_date, top_n=10):
    if not (1<=top_n<=100): top_n=max(1,min(top_n,100))
    sc=calculate_scores(target_date)
    return sorted(sc.items(), key=lambda kv: (-kv[1], kv[0]))[:top_n]
