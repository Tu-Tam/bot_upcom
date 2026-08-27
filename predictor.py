import json
from collections import Counter

BONG_DUONG = {'0':'5', '1':'6', '2':'7', '3':'8', '4':'9', '5':'0', '6':'1', '7':'2', '8':'3', '9':'4'}
BONG_AM    = {'0':'7', '1':'4', '2':'9', '3':'6', '4':'1', '5':'8', '6':'3', '7':'0', '8':'5', '9':'2'}

# Bảng bộ đề cơ bản để phủ vệt chu kỳ (8 số/bộ)
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
# 1. SOI LÔ THEO CHU KỲ VỆT (BẮT DÂY BỆT & LÔ RƠI CAO CẤP)
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
    day_before_nums = parse_numbers(results[2]) if len(results) > 2 else []

    scored_lotto = []
    for i in range(100):
        num_str = f"{i:02d}"
        gap = last_seen.get(num_str, 99)

        # Bỏ lô gan > 7 ngày
        if gap > 7:
            continue

        score = 0

        # ƯU TIÊN VỆT CẦU RƠI (Nổ 2 ngày liên tiếp -> Bắt ngày thứ 3-4)
        if num_str in today_nums and num_str in yesterday_nums:
            score += 35  # Vệt cực mạnh
        elif num_str in today_nums:
            score += 20  # Lô rơi 1 ngày

        # Nhịp chuẩn 1-2 ngày chưa ra
        if gap == 1: score += 18
        elif gap == 2: score += 12

        # Cầu lộn của lô xuất hiện 2 nháy
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
# 2. SOI ĐỀ THEO CHU KỲ VỆT (BẮT 2 ĐẦU - 2 ĐUÔI - DÀN BỘ CHUẨN)
# ==============================================================================
def analyze_and_predict_db(results):
    if not results or len(results) < 20:
        return None

    db_history = []
    for r in results[:60]:
        nums = parse_numbers(r)
        if nums:
            db_history.append(nums[0])

    if len(db_history) < 15:
        return None

    last_db = db_history[0]
    db_yest = db_history[1] if len(db_history) > 1 else '00'
    
    d1_last, d2_last = last_db[0], last_db[1]
    d1_yest, d2_yest = db_yest[0], db_yest[1]

    # --- NHẬN DIỆN VỆT ĐẦU / ĐUÔI ---
    # Kiểm tra xem Đầu hoặc Đuôi có đang chạy vệt bệt không
    is_dau_bet = (d1_last == d1_yest)
    is_duoi_bet = (d2_last == d2_yest)

    # Bắt 2 Đầu Chu Kỳ:
    if is_dau_bet:
        top_2_daus = [d1_last, BONG_DUONG.get(d1_last, '0')] # Nếu đang bệt thì bắt luôn Đầu bệt + Bóng
    else:
        # Bắt Đầu vừa về + Bóng dương đuôi kỳ trước
        top_2_daus = [d1_last, BONG_DUONG.get(d2_last, '0')]

    # Bắt 2 Đuôi Chu Kỳ:
    if is_duoi_bet:
        top_2_duois = [d2_last, BONG_AM.get(d2_last, '7')]
    else:
        top_2_duois = [d2_last, BONG_DUONG.get(d1_last, '5')]

    # --- TẠO DÀN BỘ ĐỀ (TĂNG TỶ LỆ TRÚNG VỆT MẠNH) ---
    # Lấy Bộ đề của con Đề vừa về + Bộ đề bóng
    target_set_1 = "".join(sorted([d1_last, d2_last]))
    set_numbers = []
    for key in BO_DE:
        if key == target_set_1:
            set_numbers.extend(BO_DE[key])

    # --- CHẤM ĐIỂM TOÀN BỘ BẢNG SỐ (00-99) ---
    db_last_seen = {}
    for idx, db in enumerate(db_history):
        if db not in db_last_seen:
            db_last_seen[db] = idx

    candidate_scores = []
    for i in range(100):
        num_str = f"{i:02d}"
        d1, d2 = num_str[0], num_str[1]
        gap = db_last_seen.get(num_str, 99)

        if gap == 0 or gap > 30: # Lọc Đề Gan
            continue

        score = 0

        # Ưu tiên cực cao cho 2 Đầu & 2 Đuôi theo Vệt
        if d1 in top_2_daus: score += 20
        if d2 in top_2_duois: score += 20

        # Ưu tiên các số nằm trong Bộ Đề Chu Kỳ
        if num_str in set_numbers: score += 15

        # Điểm nhịp rơi lặp lại (vệt ngắn 2 - 10 ngày)
        if 2 <= gap <= 10: score += 8

        candidate_scores.append((num_str, score))

    candidate_scores.sort(key=lambda x: x[1], reverse=True)

    # Trích xuất Dàn
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
# 3. HÀM BACKTEST GIỮ NGUYÊN
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