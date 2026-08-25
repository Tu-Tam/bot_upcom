import math
from collections import Counter, defaultdict

def calculate_z_scores(data_list):
    """Tính chỉ số Z-score chuẩn hóa xác suất toán học"""
    if not data_list:
        return {}
    counts = Counter(data_list)
    total_samples = len(data_list)
    mean = total_samples / 100.0
    variance = sum((counts[str(i).zfill(2)] - mean) ** 2 for i in range(100)) / 100.0
    std_dev = math.sqrt(variance) if variance > 0 else 1.0

    z_scores = {}
    for i in range(100):
        num_str = str(i).zfill(2)
        z_scores[num_str] = (counts[num_str] - mean) / std_dev
    return z_scores

def analyze_and_predict(historical_data):
    """
    Thuật toán v4.0: Z-Score Normalization & Cross-Frequency Dynamic Filtering
    """
    if not historical_data or len(historical_data) < 15:
        return None

    # Trích xuất danh sách 2 số cuối theo ngày (Mới nhất -> Cũ nhất)
    daily_numbers = []
    for row in historical_data:
        nums = row['numbers'] if isinstance(row, dict) else row[1]
        two_digits = [str(n)[-2:].zfill(2) for n in nums]
        daily_numbers.append(two_digits)

    # 1. TÍNH Z-SCORE NỔ 30 NGÀY & 90 NGÀY
    flat_30 = [num for day in daily_numbers[:30] for num in day]
    flat_90 = [num for day in daily_numbers[:min(90, len(daily_numbers))] for num in day]

    z_30 = calculate_z_scores(flat_30)
    z_90 = calculate_z_scores(flat_90)

    # 2. XÁC ĐỊNH NHỊP RƠI (GAP SCORE)
    last_seen = {}
    for idx, day in enumerate(daily_numbers):
        for num in day:
            if num not in last_seen:
                last_seen[num] = idx

    # 3. TỔNG HỢP MÔ HÌNH ĐIỂM
    final_scores = {}
    yesterday_set = set(daily_numbers[0])

    for i in range(100):
        num = str(i).zfill(2)
        gap = last_seen.get(num, 999)

        # Trọng số Z-Score
        score = (z_30[num] * 2.5) + (z_90[num] * 1.2)

        # Trọng số nhịp toán học (Hàm chu kỳ)
        if gap == 0:        # Lô rơi vừa nổ ngày qua
            score += 0.8
        elif 1 <= gap <= 3: # Nhịp rơi lý tưởng
            score += 3.2
        elif 4 <= gap <= 6: # Nhịp trung bình
            score += 1.5
        elif 7 <= gap <= 12:# Vùng tích lũy xác suất
            score += 0.5
        else:               # Lô gan > 12 ngày
            score -= 3.0

        final_scores[num] = score

    # 4. CHỌN BẠCH THỦ & SONG THỦ CÓ ĐỒNG THUẬN LỘN
    ranked_nums = sorted(final_scores.keys(), key=lambda x: final_scores[x], reverse=True)

    # Ưu tiên Bạch Thủ là con số mà con lộn của nó cũng nằm trong top 20 điểm cao
    bach_thu = ranked_nums[0]
    for candidate in ranked_nums[:5]:
        candidate_lon = candidate[::-1]
        if candidate_lon in ranked_nums[:25]:
            bach_thu = candidate
            break

    lon_bach_thu = bach_thu[::-1]
    song_thu = (bach_thu, lon_bach_thu) if lon_bach_thu != bach_thu else (ranked_nums[0], ranked_nums[1])

    # 5. DÀN LỌC DẠNG LƯỚI CHO TOP 5 VÀ TOP 10 (Tránh cụm đầu số)
    def extract_balanced_top(candidates, limit):
        result = []
        head_tracker = defaultdict(int)
        for n in candidates:
            head = n[0]
            if head_tracker[head] < 2:  # Giới hạn tối đa 2 con/đầu số
                result.append(n)
                head_tracker[head] += 1
            if len(result) == limit:
                break
        return result

    top_5 = extract_balanced_top(ranked_nums, 5)
    top_10 = extract_balanced_top(ranked_nums, 10)

    return {
        'bach_thu': bach_thu,
        'song_thu': song_thu,
        'top_5': top_5,
        'top_10': top_10
    }

def test_prediction_accuracy(historical_data, actual_numbers):
    pred = analyze_and_predict(historical_data)
    if not pred:
        return None

    actual_2d = [str(n)[-2:].zfill(2) for n in actual_numbers]
    actual_set = set(actual_2d)

    bt = pred['bach_thu']
    st1, st2 = pred['song_thu']
    t5 = pred['top_5']
    t10 = pred['top_10']

    return {
        'bach_thu': bt,
        'bach_thu_hit': bt in actual_set,
        'song_thu': (st1, st2),
        'song_thu_hits': sum(1 for x in (st1, st2) if x in actual_set),
        'top_5': t5,
        'top_5_hits': sum(1 for x in t5 if x in actual_set),
        'top_10': t10,
        'top_10_hits': sum(1 for x in t10 if x in actual_set),
        'actual_count': len(actual_2d),
        'actual_numbers': actual_2d
    }