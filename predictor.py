from collections import Counter, defaultdict

def analyze_and_predict(historical_data):
    """
    Thuật toán v9.0 Pro: Ensemble Scoring Matrix & Dynamic Inversion Pair
    """
    if not historical_data or len(historical_data) < 5:
        return None

    # Trích xuất dữ liệu 2 số cuối (Mới nhất -> Cũ nhất)
    daily_numbers = []
    for row in historical_data:
        nums = row['numbers'] if isinstance(row, dict) else row[1]
        two_digits = [str(n)[-2:].zfill(2) for n in nums]
        daily_numbers.append(two_digits)

    scores = {str(i).zfill(2): 0.0 for i in range(100)}

    # 1. TÍNH LẦN XUẤT HIỆN GẦN NHẤT (GAP / NHỊP RƠI)
    last_seen = {}
    for idx, day in enumerate(daily_numbers):
        for num in day:
            if num not in last_seen:
                last_seen[num] = idx

    # 2. XÁC ĐỊNH ĐẦU / ĐUÔI CÂM CỦA NGÀY HÔM QUA (DAY 0)
    yesterday_nums = daily_numbers[0]
    heads_present = {n[0] for n in yesterday_nums}
    tails_present = {n[1] for n in yesterday_nums}
    
    mute_heads = {str(h) for h in range(10)} - heads_present
    mute_tails = {str(t) for t in range(10)} - tails_present

    # 3. TÍNH ĐIỂM MA TRẬN CHO 100 CON SỐ
    for i in range(100):
        num = str(i).zfill(2)
        gap = last_seen.get(num, 999)

        # Nhịp Rơi Chuẩn
        if gap == 2 or gap == 3:
            scores[num] += 22.0
        elif gap == 1:
            scores[num] += 12.0  # Lô rơi ngày thứ 2
        elif gap == 4:
            scores[num] += 8.0
        elif gap == 0:
            scores[num] -= 5.0   # Vừa nổ ngày hôm qua
        elif gap > 7:
            scores[num] -= 999.0 # KHÓA TUYỆT ĐỐI LÔ GAN

        # Bonus Đầu/Đuôi Câm
        if num[0] in mute_heads:
            scores[num] += 10.0
        if num[1] in mute_tails:
            scores[num] += 10.0

    # 4. TẦN SUẤT 10 NGÀY GẦN NHẤT
    recent_10 = daily_numbers[:min(10, len(daily_numbers))]
    flat_10 = [num for day in recent_10 for num in day]
    count_10 = Counter(flat_10)

    for num, count in count_10.items():
        if 2 <= count <= 4:
            scores[num] += count * 4.0
        elif count > 5:
            scores[num] -= 10.0  # Phạt lô quá nóng

    # 5. CHỐNG NEO SỐ TRƯỢT HÔM TRƯỚC (ANTI-REPEAT LOGIC)
    if len(historical_data) >= 6:
        prev_data = historical_data[1:]
        prev_pred = analyze_and_predict(prev_data)
        if prev_pred:
            prev_bt = prev_pred['bach_thu']
            if prev_bt not in yesterday_nums:
                scores[prev_bt] -= 35.0  # Triệt tiêu điểm nếu hôm trước đoán sai

    # 6. LỰA CHỌN CẶP SONG THỦ ĐÔI (AUTOMATIC INVERSION PAIR)
    pair_scores = {}
    for i in range(100):
        num = str(i).zfill(2)
        lon = num[::-1]
        if num <= lon:
            if num == lon:
                # Nếu là lô kép (11, 22...) -> Tổng điểm tính bằng điểm gốc
                p_score = scores[num]
            else:
                p_score = scores[num] + scores[lon] + 5.0  # Ưu tiên cặp có số lộn
            pair_scores[(num, lon)] = p_score

    best_pair = sorted(pair_scores.keys(), key=lambda x: pair_scores[x], reverse=True)[0]

    # Chọn Bạch Thủ từ cặp tốt nhất
    if scores[best_pair[0]] >= scores[best_pair[1]]:
        bach_thu = best_pair[0]
    else:
        bach_thu = best_pair[1]

    if best_pair[0] != best_pair[1]:
        song_thu = (best_pair[0], best_pair[1])
    else:
        # Nếu cặp tốt nhất là kép -> Lấy kép + con có điểm đơn cao thứ 2
        ranked_single = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
        second = ranked_single[1] if ranked_single[0] == best_pair[0] else ranked_single[0]
        song_thu = (best_pair[0], second)

    # 7. DÀN TOP 5 VÀ TOP 10 (PHÂN TÁN RỘNG NÂNG TỶ LỆ TRÚNG)
    ranked_nums = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

    def extract_balanced_top(candidates, limit, max_per_head):
        result = []
        head_tracker = defaultdict(int)
        for n in candidates:
            head = n[0]
            if head_tracker[head] < max_per_head:
                result.append(n)
                head_tracker[head] += 1
            if len(result) == limit:
                break
        return result

    top_5 = extract_balanced_top(ranked_nums, 5, max_per_head=1)
    top_10 = extract_balanced_top(ranked_nums, 10, max_per_head=2)

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