import json
from collections import Counter

BONG_DUONG = {'0':'5', '1':'6', '2':'7', '3':'8', '4':'9', '5':'0', '6':'1', '7':'2', '8':'3', '9':'4'}
BONG_AM    = {'0':'7', '1':'4', '2':'9', '3':'6', '4':'1', '5':'8', '6':'3', '7':'0', '8':'5', '9':'2'}

BO_DE = {
    '01': ['01', '10', '06', '60', '51', '15', '56', '65'],
    '02': ['02', '20', '07', '70', '52', '25', '57', '75'],
    '03': ['03', '30', '08', '80', '53', '35', '58', '85'],
    '04': ['04', '40', '09', '90', '54', '45', '59', '95'],
    '12': ['12', '21', '17', '71', '62', '26', '67', '76'],
    '13': ['13', '31', '18', '81', '63', '36', '68', '86'],
    '14': ['14', '41', '19', '91', '64', '46', '69', '96'],
    '23': ['23', '32', '28', '82', '73', '37', '78', '87'],
    '24': ['24', '42', '29', '92', '74', '47', '79', '97'],
    '34': ['34', '43', '39', '93', '84', '48', '89', '98']
}

def parse_numbers(row):
    if not row: return []
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

# ==============================================================================
# 1. SOI LÔ TÔ & XIÊN (BẮT NHỊP CHU KỲ RƠI 2-3 NGÀY)
# ==============================================================================
def analyze_and_predict(results):
    if not results or len(results) < 15:
        return None

    last_seen = {}
    for idx, r in enumerate(results[:30]):
        for n in parse_numbers(r):
            if n not in last_seen:
                last_seen[n] = idx

    today_nums = parse_numbers(results[0])
    yesterday_nums = parse_numbers(results[1]) if len(results) > 1 else []

    scored_lotto = []
    for i in range(100):
        num_str = f"{i:02d}"
        gap = last_seen.get(num_str, 99)

        if gap > 7: # Bỏ lô gan
            continue

        score = 0

        # Lô rơi 1 ngày hoặc nổ 2 ngày
        if num_str in today_nums and num_str in yesterday_nums:
            score += 25
        elif num_str in today_nums:
            score += 18

        # Nhịp rơi vàng (1 đến 3 ngày chưa ra)
        if gap == 1: score += 22
        elif gap == 2: score += 16
        elif gap == 3: score += 12

        # Cầu lộn nháy
        rev_num = num_str[::-1]
        if today_nums.count(rev_num) >= 2:
            score += 15

        scored_lotto.append((num_str, score))

    scored_lotto.sort(key=lambda x: x[1], reverse=True)
    top_8 = [x[0] for x in scored_lotto[:8]]

    if len(top_8) < 4:
        top_8 = ["01", "10", "23", "32"]

    bach_thu = top_8[0]
    x2_pairs = []
    rev_bt = bach_thu[::-1]
    if rev_bt != bach_thu and rev_bt in top_8:
        x2_pairs.append([bach_thu, rev_bt])
    else:
        x2_pairs.append([bach_thu, top_8[1]])
        
    x2_pairs.append([top_8[1], top_8[2]])

    return {
        'bach_thu': bach_thu,
        'xien_2': x2_pairs,
        'xien_3': top_8[:3],
        'xien_4': top_8[:4]
    }

# ==============================================================================
# 2. THUẬT TOÁN ĐỀ TỐI ƯU: CẦU GHÉP BÓNG & CHẠM NỔ ĐỘNG
# ==============================================================================
def analyze_and_predict_db(results):
    if not results or len(results) < 20:
        return None

    db_history = []
    g1_history = []
    for r in results[:60]:
        nums = parse_numbers(r)
        if nums:
            db_history.append(nums[0])
            if len(nums) > 1:
                g1_history.append(nums[1])

    if len(db_history) < 15:
        return None

    last_db = db_history[0]
    d1_last, d2_last = last_db[0], last_db[1]

    # --- A. BẮT 2 ĐẦU CHÍNH XÁC ---
    # Đầu 1: Bóng Dương của Đuôi kỳ trước
    # Đầu 2: Đầu xuất hiện nhiều nhất 10 ngày qua
    daus_10 = [db[0] for db in db_history[:10] if len(db) == 2]
    most_common_daus = [item[0] for item in Counter(daus_10).most_common(2)]
    
    dau_1 = BONG_DUONG.get(d2_last, '0')
    dau_2 = most_common_daus[0] if most_common_daus[0] != dau_1 else (most_common_daus[1] if len(most_common_daus) > 1 else '1')
    top_2_daus = [dau_1, dau_2]

    # --- B. BẮT 2 ĐUÔI CHÍNH XÁC ---
    # Đuôi 1: Bóng Âm của Đuôi kỳ trước
    # Đuôi 2: Đuôi xuất hiện nhiều nhất 10 ngày qua
    duois_10 = [db[1] for db in db_history[:10] if len(db) == 2]
    most_common_duois = [item[0] for item in Counter(duois_10).most_common(2)]

    duoi_1 = BONG_AM.get(d2_last, '7')
    duoi_2 = most_common_duois[0] if most_common_duois[0] != duoi_1 else (most_common_duois[1] if len(most_common_duois) > 1 else '3')
    top_2_duois = [duoi_1, duoi_2]

    # --- C. BẮT BỘ ĐỀ & TỔNG ĐỀ VÀNG ---
    target_set = "".join(sorted([d1_last, d2_last]))
    set_numbers = []
    for key in BO_DE:
        if key == target_set:
            set_numbers.extend(BO_DE[key])

    tongs_15 = [(int(db[0]) + int(db[1])) % 10 for db in db_history[:15] if len(db) == 2]
    top_tongs = [item[0] for item in Counter(tongs_15).most_common(5)]

    db_last_seen = {}
    for idx, db in enumerate(db_history):
        if db not in db_last_seen:
            db_last_seen[db] = idx

    # --- D. LẬP DÀN & CHẤM ĐIỂM (00-99) ---
    candidate_scores = []
    for i in range(100):
        num_str = f"{i:02d}"
        d1, d2 = num_str[0], num_str[1]
        tong = (int(d1) + int(d2)) % 10
        gap = db_last_seen.get(num_str, 99)

        if gap == 0 or gap > 28: # Bỏ đề gan
            continue

        score = 0

        # Điểm Đầu - Đuôi
        if d1 in top_2_daus: score += 20
        if d2 in top_2_duois: score += 20

        # Điểm Bộ Đề & Điểm Tổng
        if num_str in set_numbers: score += 15
        if tong in top_tongs: score += 12

        # Nhịp rơi vừa nổ (2 - 12 ngày)
        if 2 <= gap <= 12: score += 8

        candidate_scores.append((num_str, score))

    candidate_scores.sort(key=lambda x: x[1], reverse=True)

    # Trích xuất dàn
    top_10 = [x[0] for x in candidate_scores[:10]]
    top_20 = [x[0] for x in candidate_scores[:20]]
    top_36 = [x[0] for x in candidate_scores[:36]]

    return {
        'dau_de': sorted(list(set(top_2_daus))),
        'duoi_de': sorted(list(set(top_2_duois))),
        'top_10_db': sorted(top_10),
        'top_20_db': sorted(top_20),
        'top_36_db': sorted(top_36)
    }

# ==============================================================================
# 3. HÀM BACKTEST
# ==============================================================================
def test_prediction_accuracy(historical_data, actual_numbers):
    if not historical_data or not actual_numbers: return None
    actual_formatted = parse_numbers(actual_numbers)
    if not actual_formatted: return None

    pred = analyze_and_predict(historical_data)
    if not pred: return None

    bt = pred['bach_thu']
    x2_list = pred['xien_2']
    x3 = pred['xien_3']
    x4 = pred['xien_4']

    x2_hits = [x for x in x2_list if all(num in actual_formatted for num in x)]
    x3_hit = len(x3) == 3 and all(num in actual_formatted for num in x3)
    x4_hit = len(x4) == 4 and all(num in actual_formatted for num in x4)

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

def test_db_accuracy(historical_data, actual_numbers):
    if not historical_data or not actual_numbers: return None
    actual_formatted = parse_numbers(actual_numbers)
    if not actual_formatted: return None

    actual_db = actual_formatted[0]
    pred_db = analyze_and_predict_db(historical_data)
    if not pred_db: return None

    return {
        'actual_db': actual_db,
        'predicted_10': pred_db.get('top_10_db', []),
        'predicted_20': pred_db.get('top_20_db', []),
        'predicted_36': pred_db.get('top_36_db', []),
        'is_hit_dau': actual_db[0] in pred_db.get('dau_de', []),
        'is_hit_duoi': actual_db[1] in pred_db.get('duoi_de', []),
        'is_hit_10': actual_db in pred_db.get('top_10_db', []),
        'is_hit_20': actual_db in pred_db.get('top_20_db', []),
        'is_hit_36': actual_db in pred_db.get('top_36_db', [])
    }