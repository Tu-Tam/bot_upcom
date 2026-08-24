from datetime import datetime, timedelta

from database import get_results
from predictor import predict


def get_dates():
    rows=get_results()
    return sorted(set(r[0] for r in rows))


def test_single_date(prediction_date):
    try: target=datetime.strptime(prediction_date,"%Y-%m-%d")
    except ValueError: raise ValueError(f"Sai ngày: {prediction_date}")
    target_date=(target+timedelta(days=1)).strftime("%Y-%m-%d")

    print("\n"+"="*60)
    print(f"BACKTEST | Ngày phân tích: {prediction_date} → Kiểm tra: {target_date}")
    rows=get_results(); print(f"🗂️ Tổng CSDL: {len(rows)} ngày")

    actual_row=None
    for r in rows:
        if r[0]==target_date: actual_row=r; break
    if not actual_row:
        print(f"⚠️ NO_RESULT: {target_date} chưa có dữ liệu")
        return {"pred":prediction_date,"target":target_date,"status":"NO_RESULT"}

    special=str(actual_row[1]).zfill(5)
    actual=str(actual_row[2]).zfill(2)
    print(f"✅ Thực tế: ĐB={special} | 2 cuối={actual}")

    preds=predict(target_date, top_n=10)
    if not preds: raise RuntimeError("predict() rỗng!")
    numbers=[n for n,_ in preds]
    print("📊 Dự đoán:", ", ".join(numbers))

    hit=actual in numbers
    rank=numbers.index(actual)+1 if hit else None
    print(f"🎯 Trúng? {hit} | Vị trí: {rank}")

    print("\n🏷️ TOP10 chi tiết:")
    for idx,(num,sc) in enumerate(preds,1):
        print(f"{idx:2d}. {num} | điểm={sc:.4f}")
    print("="*60)

    return {"pred":prediction_date,"target":target_date,"status":"OK",
            "actual":actual,"special":special,"preds":preds,"hit":hit,"rank":rank}


def run_backtest(days=30):
    try: days=int(days)
    except: days=30
    days=max(1,days)
    dates=get_dates()
    if not dates: print("❌ DB trống!"); return []

    valid=set()
    for d in dates:
        try: dt=datetime.strptime(d,"%Y-%m-%d")
        except: continue
        if (dt+timedelta(days=1)).strftime("%Y-%m-%d") in dates: valid.add(d)
    valid=sorted(valid, reverse=True)[:days]
    valid.sort()
    if not valid: print("❌ Không có chuỗi ngày hợp lệ!"); return []

    print("\n"+"#"*60)
    print(f"🚀 BẮT ĐẦU KIỂM CHỨNG: {len(valid)} ngày")
    print("#"*60)
    out=[]
    for d in valid:
        try: res=test_single_date(d); if res.get("status")=="OK": out.append(res)
        except Exception as e: print(f"\n❌ Lỗi {d}: {e}")
    print("\n"+"#"*60)
    print(f"✅ HOÀN TẤT: {len(out)} bản ghi hợp lệ")
    print("#"*60)
    return out


def summarize(results):
    if not results: return {}
    total=len(results); hits=sum(1 for r in results if r.get("hit"))
    t1=t3=t5=t10=0
    for r in results:
        rank=r.get("rank")
        if rank is None: continue
        if rank<=1: t1+=1
        if rank<=3: t3+=1
        if rank<=5: t5+=1
        if rank<=10: t10+=1
    stats={"days":total,"hits":hits,"hit_rate":hits/total,
           "top1":t1/total,"top3":t3/total,"top5":t5/total,"top10":t10/total}
    print("\n📊 TỔNG HỢP:")
    print(f"Tổng: {total} | Trúng: {hits} | Tỷ lệ: {stats['hit_rate']*100:.2f}%")
    print(f"Top1: {stats['top1']*100:.2f}% | Top3: {stats['top3']*100:.2f}% | Top5: {stats['top5']*100:.2f}% | Top10: {stats['top10']*100:.2f}%")
    return stats


if __name__=="__main__":
    kq=run_backtest(30)
    summarize(kq)
