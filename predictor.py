import json
from collections import Counter

# Bảng Ma Trận Bóng Âm / Dương dùng cho Đề & Lô
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

# --- THUẬT TOÁN DỰ ĐOÁN LÔ TÔ (MA TRẬN TRỌNG SỐ 3 LỚP) ---
def analyze_and_predict(results):
    if not results or len(results) < 5:
        return None

    data_100 = results[:100]
    data_10 = results[:10]
    data_3 = results[:3]
    today_last = parse_numbers(results[0])
    yesterday_last = parse_numbers(results[1]) if len(results) > 1 else []

    # 1. Tần suất 100 kỳ (Trọng số 0.5)
    all_100 = []
    for r in data_100:
        all_100.extend(parse_numbers(r))
    freq_100 = Counter(all_100)

    # 2. Tần suất 10 kỳ ngắn hạn (Trọng số 2.0)
    all_10 = []
    for r in data_10:
        all_10.extend(parse_numbers(r))
    freq_10 = Counter(all_10)

    # 3. Thống kê Đầu / Đuôi Câm kỳ vừa rồi
    heads = [n[0] for n in today_last if len(n) == 2]
    tails = [n[1] for n in today_last if len(n) == 2]
    cam_heads = [str(h) for h in range(10) if str(h) not in heads]
    cam_tails = [str(t) for t in range(10) if str(t) not in tails]

    # Tính điểm
    scores = {}
    for i in range(100):
        num_str = f"{i:02d}"
        f100 = freq_100.get(num_str, 0)
        f10 = freq_10.get(num_str, 0)

        # Trọng số đa tầng
        score = (f100 * 0.5) + (f10 * 2.5)

        # Lô rơi lại kỳ vừa rồi: Giữ mức điểm vừa phải
        if num_str in today_last:
            score *= 0.9

        # Lô ra 2-3 kỳ liên tiếp (Hot Streak): Tăng điểm nhẹ
        f3 = sum(1 for r in data_3 if num_str in parse_numbers(r))
        if f3 >= 2:
            score += 2.0

        # Điểm thưởng cho Đầu/Đuôi câm
        if num_str[0] in cam_heads: score += 2.0
        if num_str[1] in cam_tails: score += 2.0

        scores[num_str] = score

    # Sắp xếp số theo điểm
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    candidates = [item[0] for item in ranked]

    # Ghép Top theo Cặp Lộn
    final_top = []
    for num in candidates:
        if num not in final_top:
            final_top.append(num)
        
        pair = num[1] + num[0]
        # Ưu tiên đưa cặp lộn vào nếu thuộc top đầu
        if pair not in final_top and len(final_top) < 10:
            if candidates.index(num) < 4:
                final_top.append(pair)

    for num in candidates:
        if num not in final_top:
            final_top.append(num)
        if len(final_top) >= 10:
            break

    return {
        'bach_thu': final_top[0],
        'song_thu': [final_top[1], final_top[2]],
        'top_5': final_top[:5],
        'top_10': final_top[:10]
    }

# --- THUẬT TOÁN DỰ ĐOÁN GIẢI ĐẶC BIỆT (MA TRẬN BÓNG ÂM DƯƠNG & CHẠM KHUYẾT) ---
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

    last_db = db_history[0] # Đề kỳ gần nhất
    d1_last, d2_last = last_db[0], last_db[1]

    # Lấy danh sách Chạm & Tổng dựa trên Bóng Âm Dương của Đề kỳ trước
    target_chams = set([
        d1_last, d2_last,
        BONG_DUONG.get(d1_last, ''), BONG_DUONG.get(d2_last, ''),
        BONG_AM.get(d1_last, ''), BONG_AM.get(d2_last, '')
    ])
    target_chams = {int(c) for c in target_chams if c.isdigit()}

    # Thống kê Tổng 15 kỳ gần nhất
    tongs = [(int(db[0]) + int(db[1])) % 10 for db in db_history[:15] if len(db) == 2]
    top_tongs = [item[0] for item in Counter(tongs).most_common(5)]

    # Tạo bảng điểm cho 100 con đề
    db_scores = {}
    for i in range(100):
        num_str = f"{i:02d}"
        d1, d2 = int(num_str[0]), int(num_str[1])
        tong = (d1 + d2) % 10

        score = 0
        if d1 in target_chams: score += 3.5
        if d2 in target_chams: score += 3.5
        if tong in top_tongs: score += 2.0
        
        # Thưởng điểm cho số kép âm/dương hoặc số lộn của đề hôm qua
        if d1 == d2: score += 1.0
        if num_str == (d2_last + d1_last): score += 2.5

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
    st = pred['song_thu']
    t5 = pred['top_5']
    t10 = pred['top_10']

    return {
        'bach_thu': bt,
        'bach_thu_hit': bt in actual_formatted,
        'song_thu': st,
        'song_thu_hits': sum(1 for x in st if x in actual_formatted),
        'top_5': t5,
        'top_5_hits': sum(1 for x in t5 if x in actual_formatted),
        'top_10': t10,
        'top_10_hits': sum(1 for x in t10 if x in actual_formatted),
        'actual_numbers': actual_formatted,
        'actual_count': len(actual_formatted)
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