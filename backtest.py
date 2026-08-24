from datetime import datetime, timedelta
from database import get_results
from predictor import predict


def get_dates():
    return sorted(set(r[0] for r in get_results()))


def test_single(pred_date):
    try: tgt=datetime.strptime(pred_date,"%Y-%m-%d")
    except: raise ValueError(f"Sai định dạng: {pred_date}")
    next_day=(tgt+timedelta(days=1)).strftime("%Y-%m-%d")
    rows=get_results()
    actual=None
    for r in rows:
        if r[0]==next_day: actual=r; break
    if not actual:
        return {"pred":pred_date,"target":next_day,"status":"NO_DATA"}
    sp,last2=actual[1],actual[2]
    preds=predict(next_day,10)
    nums=[n for n,_ in preds]
    hit=last2 in nums
    rank=nums.index(last2)+1 if hit else None
    return {"pred":pred_date,"target":next_day,"status":"OK",
            "actual":last2,"special":sp,"preds":preds,"hit":hit,"rank":rank}


def run_backtest(days=30):
    days=max(1,int(days))
    dates=get_dates()
    if not dates: return []
    valid=[]
    for d in dates:
        try: dt=datetime.strptime(d,"%Y-%m-%d")
        except: continue
        if (dt+timedelta(days=1)).strftime("%Y-%m-%d") in dates: valid.append(d)
    valid=sorted(valid,reverse=True)[:days]; valid.sort()
    out=[]
    for d in valid:
        try: res=test_single(d); if res["status"]=="OK": out.append(res)
        except Exception as e: print(f"⚠️ {d}: {e}")
    return out


def summarize(results):
    if not results: return {}
    total=len(results); hits=sum(1 for x in results if x.get("hit"))
    t1=t3=t5=t10=0
    for x in results:
        rk=x.get("rank")
        if not rk: continue
        if rk<=1: t1+=1
        if rk<=3: t3+=1
        if rk<=5: t5+=1
        if rk<=10: t10+=1
    st={"days":total,"hits":hits,"hit_rate":hits/total,"top1":t1/total,"top3":t3/total,"top5":t5/total,"top10":t10/total}
    print(f"\n📊 KẾT QUẢ: {total} ngày | Trúng: {hits} | Tỷ lệ chung: {st['hit_rate']*100:.2f}%")
    print(f"Top1={st['top1']*100:.2f}% | Top3={st['top3']*100:.2f}% | Top5={st['top5']*100:.2f}% | Top10={st['top10']*100:.2f}%")
    return st


if __name__=="__main__":
    kq=run_backtest(30)
    summarize(kq)
