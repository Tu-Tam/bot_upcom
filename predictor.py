from collections import Counter
from datetime import datetime, timedelta
import math
import json

# Import các hàm từ database
try:
    from database import get_results, get_full
except ImportError:
    get_results = None
    get_full = None

MIN_HISTORY = 10
SHORT_WINDOW = 7
MEDIUM_WINDOW = 30
LONG_WINDOW = 90

WEIGHT_SHORT = 0.30
WEIGHT_MEDIUM = 0.25
WEIGHT_LONG = 0.15
WEIGHT_WEEKDAY = 0.15
WEIGHT_GAP = 0.15


def norm_num(n):
    return str(n).zfill(2)


def parse_dt(s):
    if isinstance(s, datetime):
        return s
    return datetime.strptime(str(s).split()[0], "%Y-%m-%d")


def extract_tails(rec):
    """Trích xuất danh sách 2 số cuối (lô tô) từ bản ghi dữ liệu."""
    t = []
    
    if not rec or not isinstance(rec, dict):
        return t

    # 1. Trích xuất từ giải đặc biệt
    sp = rec.get("special") or rec.get("g0")
    if sp and len(str(sp)) >= 2:
        t.append(str(sp)[-2:])
        
    # 2. Trích xuất từ các giải g1 -> g7
    for key in ["g1", "g2", "g3", "g4", "g5", "g6", "g7"]:
        g_val = rec.get(key, [])
        if isinstance(g_val, list):
            for f in g_val:
                if isinstance(f, str) and len(f) >= 2:
                    t.append(f[-2:])
                elif isinstance(f, int) and len(str(f)) >= 2:
                    t.append(str(f)[-2:])
                    
    # 3. Trích xuất nếu có cấu trúc dict "all"
    if isinstance(rec.get("all"), dict):
        t.extend(rec["all"].get("tails2", []))

    # 4. Trích xuất nếu dữ liệu lưu mảng "numbers" phẳng
    nums = rec.get("numbers", [])
    if isinstance(nums, str):
        try:
            nums = json.loads(nums)
        except:
            nums = nums.split(',')
            
    if isinstance(nums, list):
        for num in nums:
            if len(str(num)) >= 2:
                t.append(str(num)[-2:])

    return [norm_num(x) for x in t if str(x).isdigit()]


def get_history_before(target_dt):
    """Lấy dữ liệu lịch sử trước ngày chỉ định (Tối ưu cho cả Dict lẫn Tuple/List từ CSDL)."""
    tgt = parse_dt(target_dt)
    
    if not callable(get_results):
        return []
        
    rows = get_results()
    hist = []
    
    if not rows:
        return []

    for item in rows:
        d = None
        # Xử lý linh hoạt kiểu dữ liệu trả về từ DB
        if isinstance(item, dict):
            d = item.get('date')
        elif isinstance(item, (list, tuple)) and len(item) > 0:
            d = item[0]

        if d:
            try:
                dt_obj = parse_dt(d)
                if dt_obj < tgt:
                    f = get_full(d) if callable(get_full) else item
                    if not f or not isinstance(f, dict):
                        f = item if isinstance(item, dict) else {"date": d, "numbers": item[1] if len(item) > 1 else []}
                    hist.append(f)
            except Exception:
                continue

    return sorted(hist, key=lambda x: str(x.get("date", "")), reverse=True)


def freq_window(hist, win):
    c = Counter()
    for r in hist[:win]:
        c.update(extract_tails(r))
    return {norm_num(i): c.get(norm_num(i), 0) for i in range(100)}


def score_recency(hist, win):
    sc = {norm_num(i): 0.0 for i in range(100)}
    if not hist:
        return sc
    for idx, rec in enumerate(hist[:win]):
        w = math.exp(-idx / max(win / 3, 1))
        for tail in extract_tails(rec):
            sc[tail] += w
    return sc


def norm_score(dic):
    if not dic:
        return dic
    vals = list(dic.values())
    lo, hi = min(vals), max(vals)
    return {k: (v - lo) / (hi - lo) if hi != lo else 0.0 for k, v in dic.items()}


def score_weekday(hist, target_dt):
    dow = parse_dt(target_dt).weekday()
    c = Counter()
    for rec in hist:
        r_date = rec.get("date")
        if r_date:
            try:
                w_day = rec.get("weekday", parse_dt(r_date).weekday())
                if w_day == dow:
                    c.update(extract_tails(rec))
            except Exception:
                continue
    raw = {norm_num(i): c.get(norm_num(i), 0) for i in range(100)}
    return norm_score(raw)


def score_gap(hist):
    sc = {}
    for num in [norm_num(i) for i in range(100)]:
        g = len(hist)
        for idx, rec in enumerate(hist):
            if num in extract_tails(rec):
                g = idx
                break
        sc[num] = math.log1p(g)
    return norm_score(sc)


def calculate(target_dt):
    hist = get_history_before(target_dt)
    if len(hist) < MIN_HISTORY:
        raise ValueError(f"Cần ít nhất {MIN_HISTORY} ngày lịch sử (Hiện có: {len(hist)} ngày)")
    
    sh = norm_score(score_recency(hist, SHORT_WINDOW))
    md = norm_score(score_recency(hist, MEDIUM_WINDOW))
    lg = norm_score(freq_window(hist, LONG_WINDOW))
    wd = score_weekday(hist, target_dt)
    gp = score_gap(hist)
    
    total = {}
    for n in [norm_num(i) for i in range(100)]:
        total[n] = sh[n] * WEIGHT_SHORT + md[n] * WEIGHT_MEDIUM + lg[n] * WEIGHT_LONG + wd[n] * WEIGHT_WEEKDAY + gp[n] * WEIGHT_GAP
    return total


def predict(target_date, top_n=10):
    sc = calculate(target_date)
    rank = sorted(sc.items(), key=lambda kv: (-kv[1], kv[0]))
    return rank[:max(1, min(top_n, 100))]


def generate_prediction_report(results=None):
    """Tạo bản tin dự đoán dựa trên thuật toán tính điểm trọng số."""
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    try:
        predictions = predict(today_str, top_n=10)
    except Exception:
        # Nếu ngày hôm nay chưa qua giờ quay thưởng (chưa có kết quả mới), tính dự đoán dựa trên ngày mai
        tomorrow_str = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        try:
            predictions = predict(tomorrow_str, top_n=10)
        except Exception as e:
            return (
                f"⚠️ *Thông báo hệ thống dự đoán:*\n"
                f"Không thể chạy thuật toán ({e}).\n"
                "Hãy thử bấm `/capnhat` hoặc cào thêm dữ liệu lịch sử."
            )

    bTL = predictions[0][0]
    sTL = [predictions[0][0], predictions[1][0]]
    top_5 = [p[0] for p in predictions[:5]]
    
    report = (
        f"🎯 *BẢN TIN DỰ ĐOÁN XSMB HÔM NAY ({today_str})*\n"
        "------------------------------------\n"
        f"🔥 **Bạch Thủ Lô:** `{bTL}`\n"
        f"👯 **Song Thủ Lô:** `{sTL[0]} - {sTL[1]}`\n"
        f"🌟 **Top 5 Lô đẹp nhất:** `{', '.join(top_5)}` \n\n"
        "📊 *BẢNG ĐIỂM THUẬT TOÁN (TOP 10):*\n"
    )
    
    for rank, (num, score) in enumerate(predictions, 1):
        report += f"▫️ Hạng {rank:02d}: Lô `{num}` (Điểm: `{score:.2f}`)\n"
        
    report += "\n⚠️ *Lưu ý:* _Kết quả dựa trên thuật toán thống kê trọng số (Chu kỳ, Thứ, Khoảng cách gan)._"
    return report


# --- HÀM BỔ SUNG: TEST ĐỘ CHÍNH XÁC NGÀY CỐ ĐỊNH (BACKTEST) ---
def test_prediction_accuracy(target_date_str):
    """
    Kiểm tra độ chính xác dự đoán tại một ngày cố định trong lịch sử.
    Chỉ dùng dữ liệu TRƯỚC ngày target_date_str để tính toán dự đoán và đối soát với kết quả thực tế.
    """
    try:
        tgt_dt = parse_dt(target_date_str)
        normalized_target_str = tgt_dt.strftime("%Y-%m-%d")
    except Exception:
        return "⚠️ Định dạng ngày không hợp lệ. Vui lòng sử dụng định dạng `YYYY-MM-DD` (Ví dụ: `/test 2026-08-20`)."

    # 1. Lấy kết quả thực tế của ngày test từ CSDL
    if not callable(get_results):
        return "⚠️ Không thể kết nối CSDL."

    rows = get_results()
    actual_record = None
    
    if not rows:
        return "⚠️ Cơ sở dữ liệu hiện đang rỗng."
    
    # Chuẩn hóa ngày trong DB để so sánh chính xác tuyệt đối
    for r in rows:
        r_date = r.get('date') if isinstance(r, dict) else (r[0] if isinstance(r, (list, tuple)) else None)
        if r_date:
            try:
                if parse_dt(r_date).strftime("%Y-%m-%d") == normalized_target_str:
                    actual_record = get_full(r_date) if callable(get_full) else r
                    break
            except Exception:
                continue

    if not actual_record:
        return f"⚠️ Không tìm thấy dữ liệu kết quả thực tế của ngày `{normalized_target_str}` trong CSDL để đối soát.\n👉 Hãy thử bấm `/thongke` để kiểm tra các ngày hiện có."

    # Lấy danh sách lô thực tế đã về trong ngày test
    actual_tails = set(extract_tails(actual_record))
    if not actual_tails:
        return f"⚠️ Dữ liệu kết quả ngày `{normalized_target_str}` bị rỗng hoặc không hợp lệ."

    # 2. Chạy thuật toán dự đoán (chỉ dùng dữ liệu TRƯỚC ngày test)
    try:
        predictions = predict(normalized_target_str, top_n=10)
    except Exception as e:
        return f"⚠️ Không thể chạy dự đoán cho ngày `{normalized_target_str}`: {e}"

    # 3. Phân tích kết quả so sánh
    bTL = predictions[0][0]
    sTL = [predictions[0][0], predictions[1][0]]
    top5 = [p[0] for p in predictions[:5]]
    top10 = [p[0] for p in predictions[:10]]

    btl_hit = bTL in actual_tails
    stl_hits = [num for num in sTL if num in actual_tails]
    top5_hits = [num for num in top5 if num in actual_tails]
    top10_hits = [num for num in top10 if num in actual_tails]

    # 4. Tạo báo cáo chi tiết
    report = (
        f"🧪 *BÁO CÁO TEST ĐỘ CHÍNH XÁC NGÀY {normalized_target_str}*\n"
        "------------------------------------\n"
        f"🔥 **Bạch Thủ Lô (`{bTL}`):** {'✅ TRÚNG' if btl_hit else '❌ TRƯỢT'}\n"
        f"👯 **Song Thủ Lô (`{', '.join(sTL)}`):** Trúng `{len(stl_hits)}/2` lô ({', '.join(stl_hits) if stl_hits else 'Không trúng'})\n"
        f"🌟 **Top 5 Lô đẹp:** Trúng `{len(top5_hits)}/5` lô ({', '.join(top5_hits) if top5_hits else 'Không'})\n"
        f"📊 **Top 10 Lô đẹp:** Trúng `{len(top10_hits)}/10` lô ({', '.join(top10_hits) if top10_hits else 'Không'})\n\n"
        f"📝 *Tổng số giải lô về ngày đó:* `{len(actual_tails)}` đầu số.\n"
        f"ℹ️ _Lưu ý: Thuật toán chỉ sử dụng dữ liệu trước ngày {normalized_target_str} để phân tích._"
    )
    return report