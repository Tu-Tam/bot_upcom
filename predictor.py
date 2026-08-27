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

# --- THUẬT TOÁN DỰ ĐOÁN LÔ TÔ (KHUNG 45 NGÀY + NHỊP RƠI) ---
def analyze_and_predict(results):
    if not results or len(results) < 15:
        return None

    # Lấy tối đa 45 kỳ lịch sử gần nhất để phân tích nhịp lô
    data_45 = results[:45]
    
    today_last = parse_numbers(results[0])
    yesterday_last = parse_numbers(results[1]) if len(results) > 1 else []
    day_before = parse_numbers(results[2]) if len(results) > 2 else []

    # 1. Tính khoảng cách xuất hiện gần nhất (Gap) của từng con số từ 00-99
    last_seen = {}
    freq_15 = Counter()
    
    for idx, r in enumerate(data_45):
        nums = parse_numbers(r)
        if idx < 15:
            freq_15.update(nums)
        for n in nums:
            if n not in last_seen:
                last_seen[n] = idx

    # 2. Đầu / Đuôi Câm kỳ gần nhất
    heads = [n[0] for n in today_last if len(n) == 2]
    tails = [n[1] for n in today_last if len(n) == 2]
    cam_heads = [str(h) for h in range(10) if str(h) not in heads]
    cam_tails = [str(t) for t in range(10) if str(t) not in tails]

    scores = {}
    for i in range(100):
        num_str = f"{i:02d}"
        gap = last_seen.get(num_str, 99)  # Số ngày chưa về
        f15 = freq_15.get(num_str, 0)      # Tần suất trong 15 ngày qua

        score = 0.0

        # --- ĐIỂM THEO NHỊP RƠI (GAP ANALYSIS) ---
        if gap == 1:
            score += 4.5  # Nhịp rơi 1 ngày (vừa về hôm qua)
        elif gap == 2:
            score += 5.5  # Nhịp rơi 2 ngày (vừa đẹp nhất XSMB)
        elif gap == 3:
            score += 4.0  # Nhịp rơi 3 ngày
        elif gap == 0:
            # Vừa về ngày hôm nay
            if num_str in yesterday_last and num_str in day_before:
                score -= 8.0  # Đã ra 3 ngày liên tục -> Loại hẳn
            elif num_str in yesterday_last:
                score -= 3.0  # Đã ra 2 ngày -> Phạt điểm
            else:
                score += 2.0  # Lô rơi 1 nhịp
        elif gap >= 10:
            score -= 10.0  # Lô gan > 10 ngày -> Loại bỏ hoàn toàn

        # --- ĐIỂM TẦN SUẤT CHUẨN (15 NGÀY) ---
        if 2 <= f15 <= 5:
            score += 3.0  # Tần suất đều, không phải lô gan cũng không phải lô quá nóng
        elif f15 > 6:
            score += 1.0

        # --- ĐIỂM CÂM ĐẦU / ĐUÔI ---
        if num_str[0] in cam_heads: score += 2.5
        if num_str[1] in cam_tails: score += 2.5

        scores[num_str] = score

    # Tương trợ Lô Lộn (AB <-> BA)
    final_scores = {}
    for num_str, sc in scores.items():
        rev_str = num_str[::-1]
        pair_bonus = scores.get(rev_str, 0) * 0.35
        final_scores[num_str] = sc + pair_bonus

    ranked = sorted(final_scores.items(), key=lambda x: x[1], reverse=True)
    top_candidates = [item[0] for item in ranked[:6]]

    bach_thu = top_candidates[0] if top_candidates else "00"

    # GHÉP XIÊN ƯU TIÊN LÔ CẶP LỘN HOẶC TOP CAO
    xien_2_pairs = []
    # Cặp 1: Top 1 + Top 2
    xien_2_pairs.append([top_candidates[0], top_candidates[1]])
    
    # Cặp 2: Ưu tiên ghép Lộn nếu Top 1 có Lộn trong Top 6
    bt_lon = bach_thu[::-1]
    if bt_lon != bach_thu and bt_lon in top_candidates:
        xien_2_pairs.append([bach_thu, bt_lon])
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

# --- THUẬT TOÁN DỰ ĐOÁN ĐỀ (ĐẶC BIỆT CHU KỲ CHẠM TỔNG) ---
def analyze_and_predict_db(results):
    if not results or len(results) < 20:
        return None

    # Lấy lịch sử giải ĐB (số đầu tiên trong mảng parse)
    db_history = []
    for r in results[:180]:
        nums = parse_numbers(r)
        if nums:
            db_history.append(nums[0])

    if len(db_history) < 10:
        return None

    last_db = db_history[0]
    if len(last_db) < 2: return None
    
    d1_last, d2_last = last_db[0], last_db[1]

    # 1. Quét Chạm Đề Hot trong 14 ngày gần nhất
    recent_14_db = db_history[:14]
    recent_digits = [d for db in recent_14_db for d in db if len(db) == 2]
    top_chams = [c[0] for c in Counter(recent_digits).most_common(3)]

    # Bổ sung Chạm Bóng Dương & Bóng Âm của con Đề vừa ra
    chams_bo_sung = [
        d1_last, d2_last,
        BONG_DUONG.get(d2_last, ''),
        BONG_AM.get(d2_last, '')
    ]
    target_chams = list(set([c for c in top_chams + chams_bo_sung if c.isdigit()]))

    # 2. Chu kỳ Đề Thứ (Lấy đề cùng thứ tuần trước - vị trí index 7)
    same_day_last_week = db_history[7] if len(db_history) > 7 else ""
    cham_tuankhui = [same_day_last_week[0], same_day_last_week[1]] if len(same_day_last_week) == 2 else []

    # 3. Quét Tổng Đề Hot (20 ngày)
    tongs_20 = [(int(db[0]) + int(db[1])) % 10 for db in db_history[:20] if len(db) == 2]
    top_tongs = [item[0] for item in Counter(tongs_20).most_common(4)]

    db_scores = {}
    for i in range(100):
        num_str = f"{i:02d}"
        d1, d2 = num_str[0], num_str[1]
        tong = (int(d1) + int(d2)) % 10

        score = 0.0

        # Điểm Chạm Hot & Bóng
        if d1 in target_chams: score += 3.5
        if d2 in target_chams: score += 3.5

        # Điểm Chạm Tuần Khui (Chu kỳ 7 ngày)
        if d1 in cham_tuankhui or d2 in cham_tuankhui:
            score += 2.0

        # Điểm Tổng
        if tong in top_tongs: score += 3.0

        # Ưu tiên Đề lộn / Đề kép nhẹ
        if num_str == (d2_last + d1_last): score += 2.5
        if d1 == d2: score += 1.0

        # Trừ điểm Đề bệt nguyên con
        if num_str == last_db: score -= 8.0

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