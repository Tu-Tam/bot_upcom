import json
from collections import Counter

def parse_numbers(row):
    """Chuẩn hóa dữ liệu danh sách số từ CSDL"""
    nums = row.get('numbers', [])
    if isinstance(nums, str):
        try:
            nums = json.loads(nums)
        except:
            nums = nums.split(',')
    return [str(n).zfill(2)[-2:] for n in nums if str(n).strip()]

# --- THUẬT TOÁN DỰ ĐOÁN LÔ TÔ (CẢI TIẾN MA TRẬN CẶP & NHỊP RƠI) ---
def analyze_and_predict(results):
    if not results or len(results) < 10:
        return None

    data_100 = results[:100]
    recent_5 = results[:5]
    today_last = parse_numbers(results[0])

    # 1. Thống kê tần suất
    all_lottos_100 = []
    for r in data_100:
        all_lottos_100.extend(parse_numbers(r))
    freq_100 = Counter(all_lottos_100)

    all_lottos_5 = []
    for r in recent_5:
        all_lottos_5.extend(parse_numbers(r))
    freq_5 = Counter(all_lottos_5)

    # 2. Xử lý Đầu / Đuôi Câm kỳ gần nhất
    heads = [n[0] for n in today_last]
    tails = [n[1] for n in today_last]
    cam_heads = [str(h) for h in range(10) if str(h) not in heads]
    cam_tails = [str(t) for t in range(10) if str(t) not in tails]

    # 3. Tính toán điểm số trọng số linh hoạt (Dynamic Scoring)
    scores = {}
    for i in range(100):
        num_str = f"{i:02d}"
        f100 = freq_100.get(num_str, 0)
        f5 = freq_5.get(num_str, 0)
        
        # Công thức trọng số tối ưu
        score = (f100 * 1.2) + (f5 * 3.5)

        # Phạt nhẹ lô rơi (15%) thay vì phạt nặng (40%) để không bỏ sót lô bệt
        if num_str in today_last:
            score *= 0.85

        # Cộng điểm ưu tiên cho Đầu / Đuôi câm
        if num_str[0] in cam_heads: score += 2.5
        if num_str[1] in cam_tails: score += 2.5

        scores[num_str] = score

    # Sắp xếp số theo điểm số
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    top_candidates = [item[0] for item in ranked]

    # 4. Tự động kẹp Cặp Lộn vào Top 5 & Top 10
    final_top = []
    for num in top_candidates:
        if num not in final_top:
            final_top.append(num)
        
        # Lấy con lộn
        pair = num[1] + num[0]
        if pair not in final_top and len(final_top) < 10:
            # Nếu con chính có điểm cao, kéo con lộn vào ngay sau
            if top_candidates.index(num) < 3:
                final_top.append(pair)

    # Đảm bảo đủ 10 số
    for num in top_candidates:
        if num not in final_top:
            final_top.append(num)
        if len(final_top) >= 10:
            break

    bach_thu = final_top[0]
    song_thu = [final_top[1], final_top[2]]
    top_5 = final_top[:5]
    top_10 = final_top[:10]

    return {
        'bach_thu': bach_thu,
        'song_thu': song_thu,
        'top_5': top_5,
        'top_10': top_10
    }

# --- THUẬT TOÁN DỰ ĐOÁN GIẢI ĐẶC BIỆT (ĐỀ CHẠM & TỔNG TỐI ƯU) ---
def analyze_and_predict_db(results):
    if not results or len(results) < 10:
        return None

    recent_30 = results[:30]
    db_list = []
    for r in recent_30:
        nums = parse_numbers(r)
        if nums:
            db_list.append(nums[0])

    if not db_list:
        return None

    # Phân tích Chạm & Tổng
    chams = []
    tongs = []
    for db in db_list:
        d1, d2 = int(db[0]), int(db[1])
        chams.extend([d1, d2])
        tongs.append((d1 + d2) % 10)

    # Lấy 5 Chạm và 5 Tổng xuất hiện nhiều nhất
    top_chams = [item[0] for item in Counter(chams).most_common(5)]
    top_tongs = [item[0] for item in Counter(tongs).most_common(5)]

    dan_36, dan_20, dan_10 = [], [], []

    # Tạo Dàn 36 (Phủ rộng Chạm Hot + Tổng Hot)
    for i in range(100):
        num_str = f"{i:02d}"
        d1, d2 = int(num_str[0]), int(num_str[1])
        tong = (d1 + d2) % 10

        if d1 in top_chams or d2 in top_chams or tong in top_tongs:
            dan_36.append(num_str)

    # Tạo Dàn 20 (Lọc giao điểm Chạm Hot VÀ Tổng Hot)
    for num_str in dan_36:
        d1, d2 = int(num_str[0]), int(num_str[1])
        tong = (d1 + d2) % 10

        if (d1 in top_chams[:3] or d2 in top_chams[:3]) and (tong in top_tongs[:4]):
            dan_20.append(num_str)

    # Tạo Dàn 10 (Lọc siêu rút gọn từ Chạm 1-2 & Tổng 1-3)
    for num_str in dan_20:
        d1, d2 = int(num_str[0]), int(num_str[1])
        tong = (d1 + d2) % 10

        if (d1 in top_chams[:2] or d2 in top_chams[:2]) and (tong in top_tongs[:3]):
            dan_10.append(num_str)

    # Đảm bảo đủ số lượng dàn
    all_possible = [f"{i:02d}" for i in range(100)]
    
    dan_36 = (dan_36 + [x for x in all_possible if x not in dan_36])[:36]
    dan_20 = (dan_20 + [x for x in all_possible if x not in dan_20])[:20]
    dan_10 = (dan_10 + [x for x in all_possible if x not in dan_10])[:10]

    return {
        'top_10_db': sorted(dan_10),
        'top_20_db': sorted(dan_20),
        'top_36_db': sorted(dan_36)
    }

# --- HÀM BACKTEST LÔ TÔ ---
def test_prediction_accuracy(historical_data, actual_numbers):
    if not historical_data or not actual_numbers:
        return None

    actual_formatted = [str(n).zfill(2)[-2:] for n in actual_numbers]
    pred = analyze_and_predict(historical_data)
    if not pred:
        return None

    bt = pred['bach_thu']
    st = pred['song_thu']
    t5 = pred['top_5']
    t10 = pred['top_10']

    bt_hit = bt in actual_formatted
    st_hits = sum(1 for x in st if x in actual_formatted)
    t5_hits = sum(1 for x in t5 if x in actual_formatted)
    t10_hits = sum(1 for x in t10 if x in actual_formatted)

    return {
        'bach_thu': bt,
        'bach_thu_hit': bt_hit,
        'song_thu': st,
        'song_thu_hits': st_hits,
        'top_5': t5,
        'top_5_hits': t5_hits,
        'top_10': t10,
        'top_10_hits': t10_hits,
        'actual_numbers': actual_formatted,
        'actual_count': len(actual_formatted)
    }

# --- HÀM BACKTEST ĐỀ ---
def test_db_accuracy(historical_data, actual_numbers):
    if not historical_data or not actual_numbers:
        return None

    actual_formatted = [str(n).zfill(2)[-2:] for n in actual_numbers]
    actual_db = actual_formatted[0] if actual_formatted else ""

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