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

# --- THUẬT TOÁN DỰ ĐOÁN LÔ TÔ (BẠCH THỦ & XIÊN 2, 3, 4) ---
def analyze_and_predict(results):
    if not results or len(results) < 5:
        return None

    data_100 = results[:100]
    data_10 = results[:10]
    
    today_last = parse_numbers(results[0])
    yesterday_last = parse_numbers(results[1]) if len(results) > 1 else []

    # Tần suất
    all_100 = [n for r in data_100 for n in parse_numbers(r)]
    freq_100 = Counter(all_100)

    all_10 = [n for r in data_10 for n in parse_numbers(r)]
    freq_10 = Counter(all_10)

    # Đầu/Đuôi câm
    heads = [n[0] for n in today_last if len(n) == 2]
    tails = [n[1] for n in today_last if len(n) == 2]
    cam_heads = [str(h) for h in range(10) if str(h) not in heads]
    cam_tails = [str(t) for t in range(10) if str(t) not in tails]

    scores = {}
    for i in range(100):
        num_str = f"{i:02d}"
        f100 = freq_100.get(num_str, 0)
        f10 = freq_10.get(num_str, 0)

        # Trọng số nền
        score = (f100 * 0.4) + (f10 * 2.8)

        # Kiểm tra chuỗi rơi
        in_today = num_str in today_last
        in_yesterday = num_str in yesterday_last

        if in_today and in_yesterday:
            score += 3.0 # Đang rơi liên tục
        elif in_today:
            score *= 0.75 # Hạ bớt trọng số nếu mới về 1 kỳ để chống kẹt số

        # Thưởng điểm Câm
        if num_str[0] in cam_heads: score += 2.5
        if num_str[1] in cam_tails: score += 2.5

        scores[num_str] = score

    # Sắp xếp lấy các con lô có điểm cao nhất
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    top_candidates = [item[0] for item in ranked[:6]] # Lấy top 6 con đẹp nhất

    bach_thu = top_candidates[0] if top_candidates else "00"

    # Tạo cặp Xiên 2, Xiên 3, Xiên 4 an toàn
    xien_2_comb = list(combinations(top_candidates[:4], 2))[:2]
    xien_3_comb = list(combinations(top_candidates[:5], 3))[:1]
    xien_4_comb = list(combinations(top_candidates[:6], 4))[:1]

    xien_2 = [list(x) for x in xien_2_comb]
    xien_3 = list(xien_3_comb[0]) if xien_3_comb else []
    xien_4 = list(xien_4_comb[0]) if xien_4_comb else []

    return {
        'bach_thu': bach_thu,
        'xien_2': xien_2,
        'xien_3': xien_3,
        'xien_4': xien_4
    }

# --- THUẬT TOÁN DỰ ĐOÁN ĐỀ ---
def analyze_and_predict_db(results):
    if not results or len(results) < 5:
        return None

    db_history = []
    for r in results[:30]:
        nums = parse_numbers(r)
        if nums:
            db_history.append(nums[0])

    if not db_history:
        return None

    last_db = db_history[0]
    if len(last_db) < 2:
        return None
        
    d1_last, d2_last = last_db[0], last_db[1]

    target_chams = [
        d1_last, d2_last,
        BONG_DUONG.get(d1_last, ''), BONG_DUONG.get(d2_last, ''),
        BONG_AM.get(d1_last, ''), BONG_AM.get(d2_last, '')
    ]
    target_chams = [c for c in target_chams if c.isdigit()]
    cham_counts = Counter(target_chams).most_common(3)
    main_chams = [c[0] for c in cham_counts]

    tongs = [(int(db[0]) + int(db[1])) % 10 for db in db_history[:20] if len(db) == 2]
    top_tongs = [item[0] for item in Counter(tongs).most_common(5)]

    db_scores = {}
    for i in range(100):
        num_str = f"{i:02d}"
        d1, d2 = num_str[0], num_str[1]
        tong = (int(d1) + int(d2)) % 10

        score = 0.0
        if d1 in main_chams: score += 4.0
        if d2 in main_chams: score += 4.0
        if tong in top_tongs: score += 3.0
        if num_str == (d2_last + d1_last): score += 2.0
        if d1 == d2: score += 1.0

        db_scores[num_str] = score

    ranked_db = sorted(db_scores.items(), key=lambda x: x[1], reverse=True)
    sorted_numbers = [item[0] for item in ranked_db]

    return {
        'top_10_db': sorted(sorted_numbers[:10]),
        'top_20_db': sorted(sorted_numbers[:20]),
        'top_36_db': sorted(sorted_numbers[:36])
    }

# --- HÀM BACKTEST LÔ (KIỂM TRA BẠCH THỦ & XIÊN) ---
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

    # Kiểm tra Xiên trúng (Toàn bộ các số trong bộ xiên phải nằm trong KQXS)
    x2_hits = [x for x in x2_list if all(num in actual_formatted for num in x)]
    x3_hit = all(num in actual_formatted for num in x3) if x3 else False
    x4_hit = all(num in actual_formatted for num in x4) if x4 else False

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