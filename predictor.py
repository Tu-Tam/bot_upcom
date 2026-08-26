from collections import Counter, defaultdict

def analyze_and_predict_db(historical_data):
    if not historical_data or len(historical_data) < 10:
        return None

    # Lấy lịch sử 30 ngày Giải Đặc Biệt (2 số cuối)
    db_history = []
    for row in historical_data:
        nums = row['numbers'] if isinstance(row, dict) else row[1]
        if nums and len(nums) > 0:
            db_history.append(str(nums[0])[-2:].zfill(2))

    if len(db_history) < 10:
        return None

    recent_30 = db_history[:30]
    recent_7 = db_history[:7]

    # 1. Thống kê Chạm (0-9) & Tổng (0-9) với trọng số giảm dần theo thời gian
    cham_scores = defaultdict(float)
    sum_scores = defaultdict(float)
    head_scores = defaultdict(float)
    tail_scores = defaultdict(float)

    for idx, num in enumerate(recent_30):
        h, t = int(num[0]), int(num[1])
        s = (h + t) % 10
        # Trọng số: Ngày càng gần điểm càng cao
        weight = 1.0 / ((idx + 1) ** 0.4)

        cham_scores[h] += weight
        cham_scores[t] += weight
        sum_scores[s] += weight * 1.2
        
        if idx < 7:
            head_scores[h] += 2.0 / (idx + 1)
            tail_scores[t] += 2.0 / (idx + 1)

    # Lấy Top Chạm và Top Tổng mạnh nhất
    sorted_chams = [c for c, _ in sorted(cham_scores.items(), key=lambda x: x[1], reverse=True)]
    sorted_sums = [s for s, _ in sorted(sum_scores.items(), key=lambda x: x[1], reverse=True)]

    top_4_chams = sorted_chams[:4]
    top_2_sums = sorted_sums[:2]

    # 2. XÂY DỰNG DÀN 36 SỐ (Bao phủ dựa trên Top 4 Chạm + Top 2 Tổng)
    set_36 = set()
    
    # Thêm toàn bộ các số thuộc Top 4 Chạm (mỗi chạm có 19 số, lấy giao cắt)
    for i in range(100):
        s_str = f"{i:02d}"
        h, t = int(s_str[0]), int(s_str[1])
        s = (h + t) % 10
        if h in top_4_chams or t in top_4_chams or s in top_2_sums:
            set_36.add(s_str)

    # Giới hạn chuẩn xác đúng 36 con có điểm cao nhất
    def get_num_score(num_str):
        h, t = int(num_str[0]), int(num_str[1])
        s = (h + t) % 10
        return cham_scores[h] + cham_scores[t] + sum_scores[s] * 1.3 + head_scores[h] + tail_scores[t]

    top_36_db = sorted(list(set_36), key=get_num_score, reverse=True)[:36]

    # 3. XÂY DỰNG DÀN 20 SỐ (Lọc tối ưu từ Dàn 36)
    # Lọc những con vừa thuộc Top Chạm VÀ có điểm Đầu/Đuôi hot trong 7 ngày
    top_20_db = sorted(top_36_db, key=get_num_score, reverse=True)[:20]

    # 4. XÂY DỰNG DÀN 10 SỐ (Trọng tâm)
    top_10_db = sorted(top_20_db, key=lambda x: (head_scores[int(x[0])] + tail_scores[int(x[1])]), reverse=True)[:10]

    return {
        'top_10_db': sorted(top_10_db),
        'top_20_db': sorted(top_20_db),
        'top_36_db': sorted(top_36_db)
    }