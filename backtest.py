from datetime import datetime, timedelta
from database import get_results, get_date_range
from predictor import predict


def get_dates():
    rows = get_results()
    return sorted(set(r[0] for r in rows))


def test_single_date(prediction_date):
    try:
        target = datetime.strptime(prediction_date, "%Y-%m-%d")
    except ValueError:
        raise ValueError(f"Ngày không hợp lệ: {prediction_date}")

    target_date = (target + timedelta(days=1)).strftime("%Y-%m-%d")
    rows = get_results()

    actual_row = None
    for row in rows:
        if row[0] == target_date:
            actual_row = row
            break

    if not actual_row:
        return {
            "pred": prediction_date,
            "target": target_date,
            "status": "NO_DATA"
        }

    special = actual_row[1]
    actual_last2 = actual_row[2]

    try:
        predictions = predict(target_date, top_n=10)
    except Exception as e:
        raise RuntimeError(f"Lỗi gọi dự đoán: {e}")

    numbers = [num for num, _score in predictions]
    hit = actual_last2 in numbers
    rank = numbers.index(actual_last2) + 1 if hit else None

    return {
        "pred": prediction_date,
        "target": target_date,
        "status": "OK",
        "actual": actual_last2,
        "special": special,
        "preds": predictions,
        "hit": hit,
        "rank": rank
    }


def run_backtest(days=30):
    try:
        days = max(1, int(days))
    except Exception:
        days = 30

    all_dates = get_dates()
    if not all_dates:
        print("⚠️ Không có dữ liệu ngày nào trong cơ sở dữ liệu.")
        return []

    valid_dates = []
    for date_str in all_dates:
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            continue
        next_day = (dt + timedelta(days=1)).strftime("%Y-%m-%d")
        if next_day in all_dates:
            valid_dates.append(date_str)

    if not valid_dates:
        print("⚠️ Không tìm thấy cặp ngày liên tiếp hợp lệ để kiểm tra.")
        return []

    valid_dates.sort(reverse=True)
    test_set = valid_dates[:days]
    test_set.sort()

    out_results = []
    for day in test_set:
        try:
            result = test_single_date(day)
            if result.get("status") == "OK":
                out_results.append(result)
        except Exception as err:
            print(f"❌ Bỏ qua ngày {day}: {repr(err)}")

    return out_results


def summarize(results):
    if not results:
        print("\n⚠️ Không có kết quả hợp lệ để tổng hợp.")
        return {}

    total = len(results)
    hits = sum(1 for rec in results if rec.get("hit"))

    top1 = top3 = top5 = top10 = 0
    for rec in results:
        rank = rec.get("rank")
        if not rank:
            continue
        if rank <= 1:
            top1 += 1
        if rank <= 3:
            top3 += 1
        if rank <= 5:
            top5 += 1
        if rank <= 10:
            top10 += 1

    stats = {
        "days": total,
        "hits": hits,
        "hit_rate": hits / total,
        "top1": top1 / total,
        "top3": top3 / total,
        "top5": top5 / total,
        "top10": top10 / total
    }

    print("\n" + "=" * 60)
    print("📊 KẾT QUẢ TỔNG HỢP KIỂM CHỨNG LẠI")
    print(f"✅ Tổng ngày kiểm tra: {total}")
    print(f"🎯 Số lần trúng: {hits} — Tỷ lệ chung: {stats['hit_rate']*100:.2f}%")
    print(f"🥇 Top1: {stats['top1']*100:.2f}% | 🥉 Top3: {stats['top3']*100:.2f}%")
    print(f"⭐ Top5: {stats['top5']*100:.2f}% | 📎 Top10: {stats['top10']*100:.2f}%")
    print("=" * 60)

    return stats


if __name__ == "__main__":
    kq = run_backtest(30)
    summarize(kq)
