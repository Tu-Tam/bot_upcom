import json
from collections import Counter
from itertools import combinations

BONG_DUONG = {'0':'5', '1':'6', '2':'7', '3':'8', '4':'9', '5':'0', '6':'1', '7':'2', '8':'3', '9':'4'}
BONG_AM    = {'0':'7', '1':'4', '2':'9', '3':'6', '4':'1', '5':'8', '6':'3', '7':'0', '8':'5', '9':'2'}

def parse_numbers(row):
    """Trích xuất dữ liệu mảng số an toàn"""
    if not row:
        return []
    if isinstance(row, dict):
        nums = row.get('numbers') or row.get('prizes') or row.get('results') or []
        if isinstance(nums, str):
            try: nums = json.loads(nums)
            except: nums = nums.split(',')
        if isinstance(nums, list):
            return [str(n).strip().zfill(2)[-2:] for n in nums if str(n).strip()]

    if isinstance(row, str):
        try:
            parsed = json.loads(row)
            if isinstance(parsed, list):
                return [str(n).strip().zfill(2)[-2:] for n in parsed if str(n).strip()]
        except:
            return [s.strip().zfill(2)[-2:] for s in row.split(',') if s.strip()]

    if isinstance(row, list):
        return [str(n).strip().zfill(2)[-2:] for n in row if str(n).strip()]

    return []

# --- THUẬT TOÁN DỰ ĐOÁN LÔ TÔ & XIÊN TỐI ƯU ---
def analyze_and_predict(results):
    if not results or len(results) < 5:
        return None

    data_100 = results[:100]
    data_30 = results[:30]
    data_7 = results[:7]
    
    today_last = parse_numbers(results[0])
    yesterday_last = parse_numbers(results[1]) if len(results) > 1 else []
    day_before_yesterday = parse_numbers(results[2]) if len(results) > 2 else []

    # Tần suất các biên độ
    freq_100 = Counter([n for r in data_100 for n in parse_numbers(r)])
    freq_30 = Counter([n for r in data_30 for n in parse_numbers(r)])
    freq_7 = Counter([n for r in data_7 for n in parse_numbers(r)])

    # Đầu/Đuôi câm kỳ gần nhất
    heads = [n[0] for n in today_last if len(n) == 2]
    tails = [n[1] for n in today_last if len(n) == 2]
    cam_heads = [str(h) for h in range(10) if str(h) not in heads]
    cam_tails = [str(t) for t in range(10) if str(t) not in tails]

    scores = {}
    for i in range(100):
        num_str = f"{i:02d}"
        f100 = freq_100.get(num_str, 0)
        f30 = freq_30.get(num_str, 0)
        f7 = freq_7.get(num_str, 0)

        # 1. Trọng số nhịp chuẩn
        score = (f100 * 0.1) + (f30 * 0.5) + (f7 * 1.5)

        # 2. Xử lý LÔ KẸT / LÔ BỆT (Xóa bỏ tình trạng kẹt số nhiều ngày)
        in_today = num_str in today_last
        in_yesterday = num_str in yesterday_last
        in_day_before = num_str in day_before_yesterday

        if in_today and in_yesterday and in_day_before:
            score *= 0.2  # Đã ra 3 ngày liên tiếp -> Trừ điểm cực nặng
        elif in_today and in_yesterday:
            score *= 0.5  # Đã ra 2 ngày liên tiếp -> Trừ điểm nặng
        elif in_today:
            score *= 0.6  # Vừa ra hôm nay -> Giảm ưu tiên để nhường con khác rơi

        # 3. Ưu tiên Lô Nhịp Vàng (Nổ cách 1-2 ngày)
        if not in_today and in_yesterday:
            score += 2.5
        if not in_today and not in_yesterday and in_day_before:
            score += 3.5  # Nhịp rơi 2 ngày cực đẹp ở XSMB

        # 4. Thưởng điểm Câm đầu/đuôi
        if num_str[0] in cam_heads: score += 2.0
        if num_str[1] in cam_tails: score += 2.0

        scores[num_str] = score

    # Cộng điểm hỗ trợ Lô Cặp Lộn (AB - BA kéo nhau lên để ghép Xiên)
    final_scores = {}
    for num_str, sc in scores.items():
        rev_str = num_str[::-1]
        pair_score = sc + (scores.get(rev_str, 0) * 0.4)
        final_scores[num_str] = pair_score

    ranked = sorted(final_scores.items(), key=lambda x: x[1], reverse=True)
    top_candidates = [item[0] for item in ranked[:8]]

    bach_thu = top_candidates[0] if top_candidates else "00"

    # GHÉP XIÊN THÔNG MINH: Kết hợp con điểm cao nhất + Lô lộn/Lô cặp tương trợ
    xien_2_pairs = []
    # Cặp 1: Top 1 + Top 2
    xien_2_pairs.append([top_candidates[0], top_candidates[1]])
    # Cặp 2: Top 1 + Lộn của Top 1 (hoặc Top 3)
    lon_bt = bach_thu[::-1]
    if lon_bt != bach_thu and lon_bt in top_candidates:
        xien_2_pairs.append([bach_thu, lon_bt])
    else:
        xien_2_pairs.append([top_candidates[0], top_candidates[2]])

    xien_3 = top_candidates[:3]
    xien_4 = top_candidates[:4]

    return {
        'bach_thu': bach_thu,
        'xien_2': xien_2_pairs,
        'xien_3': xien_3,
        'xien_4': xien_4
    }

# --- THUẬT TOÁN DỰ ĐOÁN ĐỀ (ĐẶC BIỆT) TỐI ƯU ---
def analyze_and_predict_db(results):
    if not results or len(results) < 5:
        return None

    db_history = []
    for r in results[:40]:
        nums = parse_numbers(r)
        if nums:
            db_history.append(nums[0])

    if not db_history or len(db_history) < 5:
        return None

    # Lấy các đuôi Đề gần nhất
    last_db = db_history[0]
    if len(last_db) < 2: return None
    
    d1_last, d2_last = last_db[0], last_db[1]

    # 1. Quét ma trận Chạm (Lấy 4 Chạm mạnh nhất)
    recent_digits = [d for db in db_history[:7] for d in db]
    digit_counts = Counter(recent_digits).most_common(4)
    main_chams = [c[0] for c in digit_counts]

    # Bổ sung Chạm Bóng từ giải ĐB kỳ trước
    main_chams.append(BONG_DUONG.get(d2_last, ''))
    main_chams = list(set([c for c in main_chams if c.isdigit()]))

    # 2. Quét Ma trận Tổng Đề (Lấy 4 Tổng hot nhất)
    tongs = [(int(db[0]) + int(db[1])) % 10 for db in db_history[:15] if len(db) == 2]
    top_tongs = [item[0] for item in Counter(tongs).most_common(4)]

    db_scores = {}
    for i in range(100):
        num_str = f"{i:02d}"
        d1, d2 = num_str[0], num_str[1]
        tong = (int(d1) + int(d2)) % 10

        score = 0.0
        # Thưởng Chạm
        if d1 in main_chams: score += 3.5
        if d2 in main_chams: score += 3.5
        
        # Thưởng Tổng
        if tong in top_tongs: score += 3.0
        
        # Thưởng Đề Kép / Đề Lộn
        if d1 == d2: score += 1.5
        if num_str == (d2_last + d1_last): score += 2.0

        # Phạt Đề bệt nguyên con vừa về hôm qua
        if num_str == last_db: score -= 5.0

        db_scores[num_str] = score

    ranked_db = sorted(db_scores.items(), key=lambda x: x[1], reverse=True)
    sorted_numbers = [item[0] for item in ranked_db]

    return {
        'top_10_db': sorted(sorted_numbers[:10]),
        'top_20_db': sorted(sorted_numbers[:20]),
        'top_36_db': sorted(sorted_numbers[:36])
    }

# --- HÀM BACKTEST LÔ ---
def test_prediction_accuracy(historical_data, actual_numbers):
    if not historical_data or not actual_numbers:
        return None

    actual_formatted = parse_numbers(actual_numbers)
    if not actual_formatted:
        return None

    pred = analyze_and_predict(historical_data)
    if not pred:
        return None

    bt = pred['bach_thu']
    x2_list = pred['xien_2']
    x3 = pred['xien_3']
    x4 = pred['xien_4']

    x2_hits = [x for x in x2_list if all(num in actual_formatted for num in x)]
    x3_hit = all(num in actual_formatted for num in x3) if len(x3) == 3 and all(num in actual_formatted for num in x3) else False
    x4_hit = all(num in actual_formatted for num in x4) if len(x4) == 4 and all(num in actual_formatted for num in x4) else False

    return {
        'bach_thu': bt,
        'bach_thu_hit': bt in actual_formatted,
        'xien_2': x2_list,
        'xien_2_hits_count': len(x2_hits),
        'xien_3': x3,
        'xien_3_hit': x3_hit,
        'xien_4': x4,
        'xien_4_hit': x4_hit,
        'actual_numbers': actual_formatted
    }

# --- HÀM BACKTEST ĐỀ ---
def test_db_accuracy(historical_data, actual_numbers):
    if not historical_data or not actual_numbers:
        return None

    actual_formatted = parse_numbers(actual_numbers)
    if not actual_formatted:
        return None

    actual_db = actual_formatted[0]
    pred_db = analyze_and_predict_db(historical_data)
    if not pred_db:
        return None

    d10 = pred_db.get('top_10_db', [])
    d20 = pred_db.get('top_20_db', [])
    d36 = pred_db.get('top_36_db', [])

    return {
        'actual_db': actual_db,
        'predicted_10': d10,
        'predicted_20': d20,
        'predicted_36': d36,
        'is_hit_10': actual_db in d10,
        'is_hit_20': actual_db in d20,
        'is_hit_36': actual_db in d36
    }