import json
from collections import Counter

BONG_DUONG = {'0':'5', '1':'6', '2':'7', '3':'8', '4':'9', '5':'0', '6':'1', '7':'2', '8':'3', '9':'4'}
BONG_AM    = {'0':'7', '1':'4', '2':'9', '3':'6', '4':'1', '5':'8', '6':'3', '7':'0', '8':'5', '9':'2'}

def parse_numbers(row):
    """Trích xuất dữ liệu mảng số an toàn từ CSDL"""
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

# ==============================================================================
# 1. THUẬT TOÁN LÔ TÔ CAO CẤP: SOI CẦU ĐỘNG & BỘ LỌC TỐIƯU
# ==============================================================================
def analyze_and_predict(results):
    if not results or len(results) < 15:
        return None

    # Lấy dữ liệu 30 ngày gần nhất
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

        # Lọc Lô Gan (> 8 ngày chưa ra) và Lô bệt 3 ngày liên tiếp
        if gap >= 8 or (num_str in today_nums and num_str in yesterday_nums):
            continue

        score = 0
        
        # 1. Điểm Nhịp Rơi Chu Báo (1 - 3 ngày chưa ra có tỷ lệ nổ lại cực cao)
        if gap == 1: score += 25
        elif gap == 2: score += 20
        elif gap == 3: score += 15

        # 2. Điểm Lô Bệt (Vừa nổ hôm qua)
        if gap == 0: score += 12

        # 3. Điểm Cầu Lộn (Con lộn xuất hiện 2 nháy trở lên hôm qua)
        rev_num = num_str[::-1]
        if today_nums.count(rev_num) >= 2:
            score += 18

        # 4. Điểm Bóng Dương / Bóng Âm của con Đề vừa về
        if len(today_nums) > 0:
            last_db = today_nums[0]
            if num_str[0] == BONG_DUONG.get(last_db[1], '') or num_str[1] == BONG_AM.get(last_db[0], ''):
                score += 10

        scored_lotto.append((num_str, score))

    scored_lotto.sort(key=lambda x: x[1], reverse=True)
    top_8 = [x[0] for x in scored_lotto[:8]]

    if len(top_8) < 4:
        top_8 = ["01", "10", "23", "32"]

    bach_thu = top_8[0]
    
    # Bắt Xiên 2: Ưu tiên cặp lộn hoặc con đứng thứ 2
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
# 2. THUẬT TOÁN ĐỀ CAO CẤP: CHẠM ĐỘNG + TỔNG BIẾN THIÊN
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
    d1_last, d2_last = last_db[0], last_db[1]

    # 1. BẮT BỘ CHẠM NGUYÊN BẢN (5 Chạm vàng)
    # Chạm bệt, Bóng Dương đuôi, Bóng Âm đầu + Top 2 chữ số xuất hiện nhiều nhất 10 ngày
    digits_10 = [d for db in db_history[:10] for d in db if len(db) == 2]
    top_freq_digits = [item[0] for item in Counter(digits_10).most_common(2)]
    
    primary_chams = list(dict.fromkeys([
        d1_last, 
        d2_last, 
        BONG_DUONG.get(d2_last, '0'), 
        BONG_AM.get(d1_last, '7')
    ] + top_freq_digits))[:5]

    # 2. BẮT TỔNG ĐỀ VÀNG (6 Tổng)
    tongs_15 = [(int(db[0]) + int(db[1])) % 10 for db in db_history[:15] if len(db) == 2]
    top_tongs = [item[0] for item in Counter(tongs_15).most_common(6)]

    # 3. LẬP BẢNG THỐNG KÊ ĐỀ GAN (> 25 ngày)
    db_last_seen = {}
    for idx, db in enumerate(db_history):
        if db not in db_last_seen:
            db_last_seen[db] = idx

    # 4. CHẤM ĐIỂM DÀN 00 - 99
    candidate_scores = []
    for i in range(100):
        num_str = f"{i:02d}"
        d1, d2 = num_str[0], num_str[1]
        tong = (int(d1) + int(d2)) % 10
        gap = db_last_seen.get(num_str, 99)

        # Loại bỏ Đề Gan > 25 ngày và Bệt lại chính xác con hôm qua
        if gap == 0 or gap > 25:
            continue

        score = 0

        # Ưu tiên Chạm
        if d1 in primary_chams: score += 15
        if d2 in primary_chams: score += 15

        # Ưu tiên Tổng
        if tong in top_tongs: score += 12

        # Điểm nhịp rơi lặp lại (Chỉ số đẹp khi 2 - 12 ngày vừa nổ lại)
        if 2 <= gap <= 12: score += 8

        # Điểm Đề Kép / Kép Lệch / Lộn
        if d1 == d2: score += 5
        if num_str == (d2_last + d1_last): score += 10

        candidate_scores.append((num_str, score, d1, d2))

    # Sắp xếp điểm giảm dần
    candidate_scores.sort(key=lambda x: x[1], reverse=True)

    # 5. TRÍCH XUẤT TOP 4 ĐẦU VÀ TOP 4 ĐUÔI TỪ DÀN ĐIỂM CAO NHẤT
    top_daus_extracted = [item[0] for item in Counter([x[2] for x in candidate_scores[:25]]).most_common(4)]
    top_duois_extracted = [item[0] for item in Counter([x[3] for x in candidate_scores[:25]]).most_common(4)]

    # 6. XUẤT DÀN DỰ ĐOÁN
    top_10 = [x[0] for x in candidate_scores[:10]]
    top_20 = [x[0] for x in candidate_scores[:20]]
    top_36 = [x[0] for x in candidate_scores[:36]]

    return {
        'dau_de': sorted(top_daus_extracted),
        'duoi_de': sorted(top_duois_extracted),
        'top_10_db': sorted(top_10),
        'top_20_db': sorted(top_20),
        'top_36_db': sorted(top_36)
    }

# ==============================================================================
# 3. HÀM BACKTEST GIỮ NGUYÊN GIAO DIỆN CŨ
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