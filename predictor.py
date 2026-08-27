import json
from collections import Counter

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

# --- THUẬT TOÁN ĐỀ (ĐẶC BIỆT): MA TRẬN ĐIỂM CHẠM X TỔNG X NHỊP RƠI ---
def analyze_and_predict_db(results):
    if not results or len(results) < 20:
        return None

    db_history = []
    for r in results[:100]:
        nums = parse_numbers(r)
        if nums:
            db_history.append(nums[0])

    if len(db_history) < 15:
        return None

    last_db = db_history[0]
    d1_last, d2_last = last_db[0], last_db[1]

    # 1. BẮT 5 CHẠM TIỀM NĂNG (Bao phủ ~75% khả năng về)
    digits_15 = [d for db in db_history[:15] for d in db if len(db) == 2]
    top_freq_digits = [item[0] for item in Counter(digits_15).most_common(3)]
    
    b_duong_duoi = BONG_DUONG.get(d2_last, '0')
    b_am_dau = BONG_AM.get(d1_last, '7')
    
    # Kết hợp Top tần suất + Bóng đề kỳ trước
    primary_chams = list(dict.fromkeys([d2_last, b_duong_duoi, b_am_dau] + top_freq_digits))[:5]

    # 2. BẮT TOP 6 TỔNG CHUẨN (20 kỳ)
    tongs_20 = [(int(db[0]) + int(db[1])) % 10 for db in db_history[:20] if len(db) == 2]
    top_tongs = [item[0] for item in Counter(tongs_20).most_common(6)]

    # 3. BẮT 4 ĐẦU & 4 ĐUÔI SÁNG NHẤT
    daus_15 = [db[0] for db in db_history[:15] if len(db) == 2]
    duois_15 = [db[1] for db in db_history[:15] if len(db) == 2]
    
    top_daus = [item[0] for item in Counter(daus_15).most_common(4)]
    top_duois = [item[0] for item in Counter(duois_15).most_common(4)]

    # 4. TÍNH KHOẢNG CÁCH NỔ GẦN NHẤT (GAP)
    db_last_seen = {}
    for idx, db in enumerate(db_history[:60]):
        if db not in db_last_seen:
            db_last_seen[db] = idx

    # 5. TÍNH ĐIỂM CHI TIẾT TỪNG CON SỐ (00 - 99)
    scored_numbers = []
    for i in range(100):
        num_str = f"{i:02d}"
        d1, d2 = num_str[0], num_str[1]
        tong = (int(d1) + int(d2)) % 10
        gap = db_last_seen.get(num_str, 99)

        # Tránh Đề Gan > 30 ngày & Tránh bệt lại đúng con đề hôm qua
        if gap == 0 or gap > 30:
            continue

        score = 0

        # Cộng điểm Chạm (Đầu/Đuôi nằm trong Top Chạm)
        if d1 in primary_chams: score += 10
        if d2 in primary_chams: score += 10

        # Cộng điểm Tổng
        if tong in top_tongs: score += 8

        # Cộng điểm Đầu/Đuôi xu hướng
        if d1 in top_daus: score += 4
        if d2 in top_duois: score += 4

        # Điểm Nhịp Rơi Chuẩn (Đề hay nổ lại trong khoảng 2 - 15 ngày)
        if 2 <= gap <= 15: score += 5

        # Điểm Số Lộn / Kép
        if num_str == (d2_last + d1_last): score += 6
        if d1 == d2: score += 3

        scored_numbers.append((num_str, score))

    # Sắp xếp các con số theo tổng điểm giảm dần
    scored_numbers.sort(key=lambda x: x[1], reverse=True)

    # 6. TRÍCH XUẤT CÁC DÀN THEO TỐI ƯU ĐIỂM
    list_10 = [item[0] for item in scored_numbers[:10]]
    list_20 = [item[0] for item in scored_numbers[:20]]
    list_36 = [item[0] for item in scored_numbers[:36]]

    return {
        'dau_de': top_daus[:3],
        'duoi_de': top_duois[:3],
        'top_10_db': sorted(list_10),
        'top_20_db': sorted(list_20),
        'top_36_db': sorted(list_36)
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