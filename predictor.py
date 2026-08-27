import json
from collections import Counter

def extract_lotto_numbers(numbers):
    """ Tách 2 số cuối của tất cả các giải """
    if isinstance(numbers, str):
        try:
            numbers = json.loads(numbers)
        except:
            numbers = numbers.split(',')
    
    lotto_list = []
    for n in numbers:
        n_str = str(n).strip()
        if len(n_str) >= 2:
            lotto_list.append(n_str[-2:])
    return lotto_list

def extract_special_prize(numbers):
    """ Lấy 2 số cuối của Giải Đặc Biệt (Đề) """
    if isinstance(numbers, str):
        try:
            numbers = json.loads(numbers)
        except:
            numbers = numbers.split(',')
            
    if len(numbers) > 0:
        db_str = str(numbers[0]).strip()
        if len(db_str) >= 2:
            return db_str[-2:]
    return None


def analyze_and_predict(data):
    """
    Dự đoán LÔ TÔ - Tối ưu hóa nhịp rơi 100 kỳ
    """
    if not data:
        return {'bach_thu': '00', 'song_thu': ['00', '01'], 'top_5': [], 'top_10': []}

    data_100 = data[:100]
    all_lotto = []
    
    # 1. Thống kê tần suất
    for row in data_100:
        nums = row.get('numbers', [])
        all_lotto.extend(extract_lotto_numbers(nums))

    counts = Counter(all_lotto)
    
    # 2. Tính điểm nhịp rơi & khoảng cách (Gan)
    scores = {}
    for i in range(100):
        num_str = f"{i:02d}"
        freq = counts.get(num_str, 0)
        
        # Tìm ngày gần nhất xuất hiện
        last_seen = -1
        for idx, row in enumerate(data_100):
            if num_str in extract_lotto_numbers(row.get('numbers', [])):
                last_seen = idx
                break
        
        # Điểm tần suất base
        score = freq * 2.0
        
        # Thưởng điểm cho số đang ở nhịp rơi đẹp (3 - 7 ngày chưa về)
        if 3 <= last_seen <= 7:
            score += 8.0
        elif last_seen > 25: # Phạt điểm số quá gan
            score -= 10.0
            
        scores[num_str] = score

    sorted_lotto = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    bach_thu = sorted_lotto[0][0]
    song_thu = [sorted_lotto[0][0], sorted_lotto[1][0]]
    top_5 = [x[0] for x in sorted_lotto[:5]]
    top_10 = [x[0] for x in sorted_lotto[:10]]

    return {
        'bach_thu': bach_thu,
        'song_thu': song_thu,
        'top_5': top_5,
        'top_10': top_10
    }


def analyze_and_predict_db(data):
    """
    Dự đoán GIẢI ĐẶC BIỆT (ĐỀ) - Thuật toán Ma trận 5 Nhân tố (High Win-Rate)
    """
    if not data:
        return {'top_10_db': [], 'top_20_db': [], 'top_36_db': []}

    data_100 = data[:100]
    
    db_history = []
    heads = []
    tails = []
    sums = []
    
    for row in data_100:
        nums = row.get('numbers', [])
        db_val = extract_special_prize(nums)
        if db_val and len(db_val) == 2:
            db_history.append(db_val)
            h, t = int(db_val[0]), int(db_val[1])
            heads.append(h)
            tails.append(t)
            sums.append((h + t) % 10)

    if not db_history:
        return {'top_10_db': [], 'top_20_db': [], 'top_36_db': []}

    # Dem tần suất
    count_db = Counter(db_history)
    count_head = Counter(heads)
    count_tail = Counter(tails)
    count_sum = Counter(sums)

    # Lấy thông tin kỳ vừa về gần nhất
    last_db = db_history[0]
    last_h, last_t = int(last_db[0]), int(last_db[1])
    
    # Bóng dương: 0-5, 1-6, 2-7, 3-8, 4-9
    bg_h = (last_h + 5) % 10
    bg_t = (last_t + 5) % 10

    scores = {}

    for i in range(100):
        num_str = f"{i:02d}"
        h, t = int(num_str[0]), int(num_str[1])
        s = (h + t) % 10

        # --- YẾU TỐ 1: Tần suất Trục Đầu - Đuôi - Tổng (Weight cao) ---
        score = (count_head[h] * 3.5) + (count_tail[t] * 3.5) + (count_sum[s] * 2.5)

        # --- YẾU TỐ 2: Tần suất chính xác con số đó ---
        score += count_db.get(num_str, 0) * 5.0

        # --- YẾU TỐ 3: Bắt Cầu Bóng & Chạm Kỳ Trước ---
        if h == bg_h or t == bg_t:
            score += 6.0  # Ưu tiên bóng
        if h == last_h or t == last_t:
            score += 4.0  # Ưu tiên giữ chạm

        # --- YẾU TỐ 4: Phân tích Nhịp Gan (Khoảng cách nổ) ---
        last_seen_idx = -1
        for idx, val in enumerate(db_history):
            if val == num_str:
                last_seen_idx = idx
                break
        
        if last_seen_idx == -1 or last_seen_idx > 40:
            score -= 12.0  # Trừ điểm nặng đề quá gan (>40 ngày)
        elif 8 <= last_seen_idx <= 20:
            score += 7.0   # Thưởng điểm khung nhịp rơi chuẩn (8-20 ngày)
            
        scores[num_str] = score

    # Sắp xếp danh sách theo Điểm số giảm dần
    sorted_db = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    top_10 = [x[0] for x in sorted_db[:10]]
    top_20 = [x[0] for x in sorted_db[:20]]
    top_36 = [x[0] for x in sorted_db[:36]]

    return {
        'top_10_db': top_10,
        'top_20_db': top_20,
        'top_36_db': top_36
    }


def test_prediction_accuracy(historical_data, actual_numbers):
    """ Test độ chính xác LÔ """
    if not historical_data or not actual_numbers:
        return None

    pred = analyze_and_predict(historical_data)
    actual_lotto = extract_lotto_numbers(actual_numbers)

    return {
        'bach_thu': pred['bach_thu'],
        'bach_thu_hit': pred['bach_thu'] in actual_lotto,
        'song_thu': pred['song_thu'],
        'song_thu_hits': sum(1 for x in pred['song_thu'] if x in actual_lotto),
        'top_5': pred['top_5'],
        'top_5_hits': sum(1 for x in pred['top_5'] if x in actual_lotto),
        'top_10': pred['top_10'],
        'top_10_hits': sum(1 for x in pred['top_10'] if x in actual_lotto),
        'actual_numbers': actual_lotto,
        'actual_count': len(actual_lotto)
    }


def test_db_accuracy(historical_data, actual_numbers):
    """ Test độ chính xác GIẢI ĐẶC BIỆT """
    if not historical_data or not actual_numbers:
        return None

    actual_db = extract_special_prize(actual_numbers)
    if not actual_db:
        return None

    pred_db = analyze_and_predict_db(historical_data)

    return {
        'actual_db': actual_db,
        'predicted_10': pred_db.get('top_10_db', []),
        'predicted_20': pred_db.get('top_20_db', []),
        'predicted_36': pred_db.get('top_36_db', []),
        'is_hit_10': actual_db in pred_db.get('top_10_db', []),
        'is_hit_20': actual_db in pred_db.get('top_20_db', []),
        'is_hit_36': actual_db in pred_db.get('top_36_db', []),
        'is_hit': actual_db in pred_db.get('top_10_db', [])
    }