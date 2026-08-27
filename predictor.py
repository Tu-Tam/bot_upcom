import json
from collections import Counter
from itertools import combinations

BONG_DUONG = {'0':'5', '1':'6', '2':'7', '3':'8', '4':'9', '5':'0', '6':'1', '7':'2', '8':'3', '9':'4'}
BONG_AM    = {'0':'7', '1':'4', '2':'9', '3':'6', '4':'1', '5':'8', '6':'3', '7':'0', '8':'5', '9':'2'}

def parse_numbers(row):
    """Trích xuất dữ liệu mảng số an toàn từ nhiều định dạng khác nhau"""
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

# --- THUẬT TOÁN LÔ TÔ & XIÊN: TRỌNG SỐ ĐA TẦNG ---
def analyze_and_predict(results):
    if not results or len(results) < 10:
        return None

    data_30 = results[:30]
    today_last = parse_numbers(results[0])
    yesterday_last = parse_numbers(results[1]) if len(results) > 1 else []

    # 1. Đoạn thời gian xuất hiện gần nhất (Gap)
    last_seen = {}
    for idx, r in enumerate(data_30):
        for n in parse_numbers(r):
            if n not in last_seen:
                last_seen[n] = idx

    # 2. Tần suất xuất hiện (10 kỳ & 20 kỳ)
    all_10 = [n for r in results[:10] for n in parse_numbers(r)]
    all_20 = [n for r in results[:20] for n in parse_numbers(r)]
    freq_10 = Counter(all_10)
    freq_20 = Counter(all_20)

    # 3. Chấm điểm ứng viên
    candidates = []
    for num in range(100):
        num_str = f"{num:02d}"
        gap = last_seen.get(num_str, 99)
        f10 = freq_10.get(num_str, 0)
        f20 = freq_20.get(num_str, 0)

        # Tránh Lô Gan > 8 ngày & Lô rơi quá 3 ngày
        if gap >= 9:
            continue
        if num_str in today_last and num_str in yesterday_last:
            continue

        score = 0

        # Điểm Nhịp Rơi
        if gap in [1, 2]: score += 15       # Nhịp rơi ngắn chuẩn
        elif gap == 3: score += 10
        elif gap == 4: score += 6

        # Điểm Phong Độ (Tần suất)
        if 2 <= f10 <= 4: score += 10
        if 4 <= f20 <= 8: score += 8

        # Ưu tiên Lô Cặp Lộn có phong độ đều (VD: cả 12 và 21 đều nổ gối đầu)
        rev_num = num_str[::-1]
        if freq_10.get(rev_num, 0) >= 2:
            score += 5

        candidates.append((num_str, score, f10, f20))

    # Sắp xếp chọn Top
    candidates.sort(key=lambda x: (x[1], x[2], x[3]), reverse=True)
    top_nums = [c[0] for c in candidates[:8]]

    if len(top_nums) < 4:
        top_nums = ["01", "10", "23", "32"]

    bach_thu = top_nums[0]
    
    # 4. Tối ưu ghép Xiên: Kết hợp Top Điểm Cao + Cặp Lộn
    xien_2_pairs = []
    
    # Cặp Xiên 1: Bạch thủ + Lót lộn (nếu có trong top) hoặc Top 2
    rev_bt = bach_thu[::-1]
    if rev_bt != bach_thu and rev_bt in top_nums:
        xien_2_pairs.append([bach_thu, rev_bt])
    else:
        xien_2_pairs.append([bach_thu, top_nums[1]])

    # Cặp Xiên 2: Ghép Top 2 + Top 3
    xien_2_pairs.append([top_nums[1], top_nums[2]])

    # Cặp Xiên 3 & Xiên 4: Lấy trực tiếp Top 3 và Top 4 điểm cao nhất
    xien_3 = top_nums[:3]
    xien_4 = top_nums[:4]

    return {
        'bach_thu': bach_thu,
        'xien_2': xien_2_pairs,
        'xien_3': xien_3,
        'xien_4': xien_4
    }

# --- THUẬT TOÁN ĐỀ (ĐẶC BIỆT): THỐNG KÊ CHẠM X TỔNG X TẦN SUẤT 20 NGÀY ---
def analyze_and_predict_db(results):
    if not results or len(results) < 20:
        return None

    db_history = []
    for r in results[:60]:
        nums = parse_numbers(r)
        if nums:
            db_history.append(nums[0])

    if len(db_history) < 10:
        return None

    last_db = db_history[0]
    d1_last, d2_last = last_db[0], last_db[1]

    # 1. XÁC ĐỊNH 3 CHẠM CHỦ LỰC (Phân bổ theo tần suất 15 ngày + Bóng âm dương)
    all_digits_15 = [d for db in db_history[:15] for d in db if len(db) == 2]
    top_digits = [item[0] for item in Counter(all_digits_15).most_common(3)]
    
    # Thêm bóng dương đề hôm qua nếu chưa thuộc top
    bong_duong_duoi = BONG_DUONG.get(d2_last, '0')
    if bong_duong_duoi not in top_digits:
        top_digits[2] = bong_duong_duoi

    selected_chams = list(set(top_digits))

    # 2. XÁC ĐỊNH 4 TỔNG CHỦ LỰC (Tần suất tổng trong 25 kỳ)
    tongs_25 = [(int(db[0]) + int(db[1])) % 10 for db in db_history[:25] if len(db) == 2]
    top_tongs = [item[0] for item in Counter(tongs_25).most_common(4)]

    # 3. XÁC ĐỊNH 3 ĐẦU & 3 ĐUÔI SÁNG NHẤT
    daus_15 = [db[0] for db in db_history[:15] if len(db) == 2]
    duois_15 = [db[1] for db in db_history[:15] if len(db) == 2]
    
    top_daus = [item[0] for item in Counter(daus_15).most_common(3)]
    top_duois = [item[0] for item in Counter(duois_15).most_common(3)]

    # 4. ĐÁNH GIÁ VÀ XẾP HẠNG 100 CON SỐ DÀN ĐỀ
    scored_numbers = []
    for i in range(100):
        num_str = f"{i:02d}"
        d1, d2 = num_str[0], num_str[1]
        tong = (int(d1) + int(d2)) % 10

        score = 0
        # Điểm Chạm
        if d1 in selected_chams or d2 in selected_chams:
            score += 10
        # Điểm Tổng
        if tong in top_tongs:
            score += 8
        # Điểm Đầu/Đuôi
        if d1 in top_daus: score += 4
        if d2 in top_duois: score += 4
        # Ưu tiên Đề Kép hoặc Đề Lộn
        if d1 == d2 or num_str == (d2_last + d1_last):
            score += 3

        scored_numbers.append((num_str, score))

    # Sắp xếp số theo điểm từ cao xuống thấp
    scored_numbers.sort(key=lambda x: x[1], reverse=True)

    # 5. TẠO CÁC DÀN ĐỀ DỰA TRÊN ĐIỂM SỐ
    list_10 = [item[0] for item in scored_numbers[:10]]
    list_20 = [item[0] for item in scored_numbers[:20]]
    list_36 = [item[0] for item in scored_numbers[:36]]

    return {
        'dau_de': top_daus,
        'duoi_de': top_duois,
        'top_10_db': sorted(list_10),
        'top_20_db': sorted(list_20),
        'top_36_db': sorted(list_36)
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

    actual_dau = actual_db[0] if len(actual_db) == 2 else ''
    actual_duoi = actual_db[1] if len(actual_db) == 2 else ''

    return {
        'actual_db': actual_db,
        'predicted_10': d10,
        'predicted_20': d20,
        'predicted_36': d36,
        'is_hit_dau': actual_dau in pred_db.get('dau_de', []),
        'is_hit_duoi': actual_duoi in pred_db.get('duoi_de', []),
        'is_hit_10': actual_db in d10,
        'is_hit_20': actual_db in d20,
        'is_hit_36': actual_db in d36
    }