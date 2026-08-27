import json
from collections import Counter

def parse_numbers(row):
    """
    Hàm chuẩn hóa CSDL an toàn 100%, chống lỗi 'Thiếu CSDL'
    """
    if not row:
        return []
    
    # Nếu là dict
    if isinstance(row, dict):
        nums = row.get('numbers') or row.get('prizes') or row.get('results') or []
        if isinstance(nums, str):
            try: nums = json.loads(nums)
            except: nums = nums.split(',')
        if isinstance(nums, list):
            res = []
            for n in nums:
                s = str(n).strip()
                if s: res.append(s.zfill(2)[-2:])
            return res

    # Nếu là string
    if isinstance(row, str):
        try:
            parsed = json.loads(row)
            if isinstance(parsed, list):
                return [str(n).zfill(2)[-2:] for n in parsed if str(n).strip()]
        except:
            return [s.zfill(2)[-2:] for s in row.split(',') if s.strip()]

    # Nếu là list
    if isinstance(row, list):
        return [str(n).zfill(2)[-2:] for n in row if str(n).strip()]

    return []

# --- THUẬT TOÁN DỰ ĐOÁN LÔ TÔ (CÂN BẰNG TẦN SUẤT & BIÊN ĐỘ) ---
def analyze_and_predict(results):
    if not results or len(results) < 5:
        return None

    data_100 = results[:100]
    data_10 = results[:10]
    data_3 = results[:3]

    # 1. Tần suất 100 ngày (Trọng số 1.0)
    all_100 = []
    for r in data_100:
        all_100.extend(parse_numbers(r))
    freq_100 = Counter(all_100)

    # 2. Tần suất 10 ngày gần nhất (Trọng số 2.5 - Hot Trend)
    all_10 = []
    for r in data_10:
        all_10.extend(parse_numbers(r))
    freq_10 = Counter(all_10)

    # 3. Lô vừa ra ngày gần nhất
    today_nums = parse_numbers(results[0])

    # Tính điểm cho 100 con số (00 - 99)
    scores = {}
    for i in range(100):
        num_str = f"{i:02d}"
        f100 = freq_100.get(num_str, 0)
        f10 = freq_10.get(num_str, 0)

        # Công thức tính điểm chuẩn
        score = (f100 * 0.8) + (f10 * 2.2)

        # Phạt nhẹ lô rơi bệt (trừ 15% điểm nếu vừa ra hôm qua)
        if num_str in today_nums:
            score *= 0.85

        scores[num_str] = score

    # Sắp xếp số theo điểm cao xuống thấp
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    top_candidates = [item[0] for item in ranked]

    # Kẹp cặp lộn tự động vào Top 5 / Top 10
    final_top = []
    for num in top_candidates:
        if num not in final_top:
            final_top.append(num)
        
        pair = num[1] + num[0]
        if pair not in final_top and len(final_top) < 10:
            if top_candidates.index(num) < 3: # Nếu thuộc Top 3 thì kéo con lộn đi cùng
                final_top.append(pair)

    for num in top_candidates:
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

# --- THUẬT TOÁN DỰ ĐOÁN GIẢI ĐẶC BIỆT (CHẠM & TỔNG) ---
def analyze_and_predict_db(results):
    if not results or len(results) < 5:
        return None

    db_list = []
    for r in results[:30]:
        nums = parse_numbers(r)
        if nums:
            db_list.append(nums[0]) # Số đầu tiên là Đề Giải Đặc Biệt

    if not db_list:
        return None

    # Thống kê Chạm và Tổng
    chams, tongs = [], []
    for db in db_list:
        if len(db) >= 2 and db.isdigit():
            d1, d2 = int(db[0]), int(db[1])
            chams.extend([d1, d2])
            tongs.append((d1 + d2) % 10)

    top_chams = [item[0] for item in Counter(chams).most_common(6)]
    top_tongs = [item[0] for item in Counter(tongs).most_common(6)]

    # Đánh điểm cho 100 số đề
    db_scores = {}
    for i in range(100):
        num_str = f"{i:02d}"
        d1, d2 = int(num_str[0]), int(num_str[1])
        tong = (d1 + d2) % 10

        score = 0
        if d1 in top_chams: score += 3.0
        if d2 in top_chams: score += 3.0
        if tong in top_tongs: score += 2.5
        
        db_scores[num_str] = score

    # Sắp xếp số đề theo điểm số
    ranked_db = sorted(db_scores.items(), key=lambda x: x[1], reverse=True)
    sorted_numbers = [item[0] for item in ranked_db]

    # Chuẩn hóa Dàn 10, 20, 36 theo thứ tự điểm cao nhất
    dan_10 = sorted_numbers[:10]
    dan_20 = sorted_numbers[:20]
    dan_36 = sorted_numbers[:36]

    return {
        'top_10_db': sorted(dan_10),
        'top_20_db': sorted(dan_20),
        'top_36_db': sorted(dan_36)
    }

# --- HÀM BACKTEST LÔ TÔ ---
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

    actual_db = actual_formatted[0] # Đề là con số đầu tiên
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