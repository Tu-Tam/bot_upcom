from collections import Counter
from datetime import datetime

def analyze_and_predict(historical_data):
    """
    Phân tích dữ liệu 365 ngày với thuật toán Đa Trọng Số (Multi-factor scoring)
    """
    if not historical_data or len(historical_data) < 10:
        return None

    # 1. Trích xuất dữ liệu lô 2 số cuối
    all_dates = []
    daily_numbers = []
    
    for row in historical_data:
        # Giả định row là dict có 'date' và 'numbers' hoặc tuple
        d_str = row['date'] if isinstance(row, dict) else row[0]
        nums = row['numbers'] if isinstance(row, dict) else row[1]
        
        # Chỉ lấy 2 số cuối của mỗi giải
        two_digits = [str(n)[-2:].zfill(2) for n in nums]
        daily_numbers.append(two_digits)
        all_dates.append(d_str)

    # 2. Tính toán các chỉ số thống kê
    scores = {str(i).zfill(2): 0.0 for i in range(100)}
    
    # Factor A: Tần suất ngắn hạn (14 ngày gần nhất - Trọng số 40%)
    recent_14 = daily_numbers[:14]
    flat_14 = [num for day in recent_14 for num in day]
    count_14 = Counter(flat_14)
    for num, count in count_14.items():
        if count <= 4:  # Nhịp chạy đẹp
            scores[num] += count * 4.0
        else:          # Nổ quá nhiều (dễ dính nhịp nghỉ)
            scores[num] += 2.0

    # Factor B: Nhịp Gan/Biên độ vắng (Trọng số 30%)
    last_seen = {}
    for idx, day in enumerate(daily_numbers):
        for num in day:
            if num not in last_seen:
                last_seen[num] = idx

    for num in scores:
        gap = last_seen.get(num, 999)
        if 2 <= gap <= 6:     # Điểm rơi đẹp nhất (vắng 2 - 6 ngày)
            scores[num] += 15.0
        elif gap == 1:        # Vừa ra hôm qua (lô rơi)
            scores[num] += 5.0
        elif gap > 15:        # Lô gan (Tránh chọn)
            scores[num] -= 10.0

    # Factor C: Thống kê tổng quan 365 ngày (Trọng số 30%)
    flat_all = [num for day in daily_numbers for num in day]
    count_all = Counter(flat_all)
    avg_count = len(flat_all) / 100.0
    for num in scores:
        freq_ratio = count_all[num] / avg_count
        scores[num] += freq_ratio * 5.0

    # 3. Sắp xếp danh sách theo điểm số giảm dần
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    top_numbers = [item[0] for item in sorted_scores]

    # 4. Chắt lọc Bạch thủ, Song thủ (kèm lộn), Top 5, Top 10
    bach_thu = top_numbers[0]
    
    # Song thủ: Lấy con cao điểm nhất + Con lộn của nó (Nếu trùng thì lấy con tiếp theo)
    lon_bach_thu = bach_thu[::-1]
    if lon_bach_thu != bach_thu and lon_bach_thu in top_numbers:
        song_thu = (bach_thu, lon_bach_thu)
    else:
        song_thu = (top_numbers[0], top_numbers[1])

    top_5 = top_numbers[:5]
    top_10 = top_numbers[:10]

    return {
        'bach_thu': bach_thu,
        'song_thu': song_thu,
        'top_5': top_5,
        'top_10': top_10
    }

def test_prediction_accuracy(historical_data, actual_numbers):
    """
    Hàm kiểm tra độ chính xác của thuật toán cho lệnh /test
    """
    pred = analyze_and_predict(historical_data)
    if not pred:
        return None

    # Lấy 2 số cuối của kết quả thực tế ngày hôm đó
    actual_2d = [str(n)[-2:].zfill(2) for n in actual_numbers]
    actual_set = set(actual_2d)

    bt = pred['bach_thu']
    st1, st2 = pred['song_thu']
    t5 = pred['top_5']
    t10 = pred['top_10']

    # Kiểm tra kết quả trúng/trượt
    bt_hit = bt in actual_set
    st_hits = sum(1 for x in (st1, st2) if x in actual_set)
    t5_hits = sum(1 for x in t5 if x in actual_set)
    t10_hits = sum(1 for x in t10 if x in actual_set)

    return {
        'bach_thu': bt,
        'bach_thu_hit': bt_hit,
        'song_thu': (st1, st2),
        'song_thu_hits': st_hits,
        'top_5': t5,
        'top_5_hits': t5_hits,
        'top_10': t10,
        'top_10_hits': t10_hits,
        'actual_count': len(actual_2d),
        'actual_numbers': actual_2d
    }