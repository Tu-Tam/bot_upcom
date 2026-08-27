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
    Phân tích LÔ TÔ dựa trên dải dữ liệu truyền vào (Tối đa 100 kỳ gần nhất)
    """
    if not data:
        return {'bach_thu': '00', 'song_thu': ['00', '01'], 'top_5': [], 'top_10': []}

    # Giới hạn tối đa 100 kỳ gần nhất để đảm bảo nhịp rơi chính xác
    data_100 = data[:100]

    all_lotto = []
    for row in data_100:
        nums = row.get('numbers', [])
        lottos = extract_lotto_numbers(nums)
        all_lotto.extend(lottos)

    counts = Counter(all_lotto)
    # Đảm bảo có đủ từ 00 đến 99 trong bảng đếm
    for i in range(100):
        num_str = f"{i:02d}"
        if num_str not in counts:
            counts[num_str] = 0

    most_common = counts.most_common()

    bach_thu = most_common[0][0]
    song_thu = [most_common[0][0], most_common[1][0]]
    top_5 = [item[0] for item in most_common[:5]]
    top_10 = [item[0] for item in most_common[:10]]

    return {
        'bach_thu': bach_thu,
        'song_thu': song_thu,
        'top_5': top_5,
        'top_10': top_10
    }

def analyze_and_predict_db(data):
    """
    Phân tích GIẢI ĐẶC BIỆT (ĐỀ ĐUÔI) dựa trên 100 kỳ gần nhất
    """
    if not data:
        return {'top_10_db': [], 'top_20_db': [], 'top_36_db': []}

    # Ép dữ liệu về đúng 100 kỳ gần nhất
    data_100 = data[:100]

    db_history = []
    heads = []
    tails = []

    for row in data_100:
        nums = row.get('numbers', [])
        db_val = extract_special_prize(nums)
        if db_val and len(db_val) == 2:
            db_history.append(db_val)
            heads.append(db_val[0])
            tails.append(db_val[1])

    if not db_history:
        return {'top_10_db': [], 'top_20_db': [], 'top_36_db': []}

    # Thống kê tần suất Lô/Đề về nhiều nhất
    db_counts = Counter(db_history)
    head_counts = Counter(heads)
    tail_counts = Counter(tails)

    # Đánh giá điểm từng con lô đề từ 00 - 99 dựa trên Chạm Đầu + Chạm Đuôi + Tần suất
    scored_numbers = []
    for i in range(100):
        num_str = f"{i:02d}"
        h, t = num_str[0], num_str[1]
        
        # Công thức tính ma trận điểm weighted score
        score = (db_counts.get(num_str, 0) * 3) + (head_counts.get(h, 0) * 1.5) + (tail_counts.get(t, 0) * 1.5)
        scored_numbers.append((num_str, score))

    # Sắp xếp theo điểm số giảm dần
    scored_numbers.sort(key=lambda x: x[1], reverse=True)

    top_10 = [item[0] for item in scored_numbers[:10]]
    top_20 = [item[0] for item in scored_numbers[:20]]
    top_36 = [item[0] for item in scored_numbers[:36]]

    return {
        'top_10_db': top_10,
        'top_20_db': top_20,
        'top_36_db': top_36
    }

def test_prediction_accuracy(historical_data, actual_numbers):
    """ Test độ chính xác của dự đoán LÔ TÔ """
    if not historical_data or not actual_numbers:
        return None

    pred = analyze_and_predict(historical_data)
    actual_lotto = extract_lotto_numbers(actual_numbers)

    bt_hit = pred['bach_thu'] in actual_lotto
    st_hits = sum(1 for x in pred['song_thu'] if x in actual_lotto)
    t5_hits = sum(1 for x in pred['top_5'] if x in actual_lotto)
    t10_hits = sum(1 for x in pred['top_10'] if x in actual_lotto)

    return {
        'bach_thu': pred['bach_thu'],
        'bach_thu_hit': bt_hit,
        'song_thu': pred['song_thu'],
        'song_thu_hits': st_hits,
        'top_5': pred['top_5'],
        'top_5_hits': t5_hits,
        'top_10': pred['top_10'],
        'top_10_hits': t10_hits,
        'actual_numbers': actual_lotto,
        'actual_count': len(actual_lotto)
    }

def test_db_accuracy(historical_data, actual_numbers):
    """ Test độ chính xác của dàn GIẢI ĐẶC BIỆT """
    if not historical_data or not actual_numbers:
        return None

    actual_db = extract_special_prize(actual_numbers)
    if not actual_db:
        return None

    pred_db = analyze_and_predict_db(historical_data)

    is_hit_10 = actual_db in pred_db.get('top_10_db', [])
    is_hit_20 = actual_db in pred_db.get('top_20_db', [])
    is_hit_36 = actual_db in pred_db.get('top_36_db', [])

    return {
        'actual_db': actual_db,
        'predicted_10': pred_db.get('top_10_db', []),
        'predicted_20': pred_db.get('top_20_db', []),
        'predicted_36': pred_db.get('top_36_db', []),
        'is_hit_10': is_hit_10,
        'is_hit_20': is_hit_20,
        'is_hit_36': is_hit_36,
        'is_hit': is_hit_10  # Tương thích ngược với code cũ
    }