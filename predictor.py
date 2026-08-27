import json
from collections import Counter
from itertools import combinations

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

# --- THUẬT TOÁN LÔ TÔ: LỌC THEO MA TRẬN NHỊP RƠI & TẦN SUẤT ---
def analyze_and_predict(results):
    if not results or len(results) < 10:
        return None

    data_30 = results[:30]
    today_last = parse_numbers(results[0])
    yesterday_last = parse_numbers(results[1]) if len(results) > 1 else []

    # 1. Tính khoảng cách (Gap) xuất hiện gần đây nhất
    last_seen = {}
    for idx, r in enumerate(data_30):
        for n in parse_numbers(r):
            if n not in last_seen:
                last_seen[n] = idx

    # 2. Tính tần suất xuất hiện trong 15 kỳ gần đây
    all_15 = [n for r in results[:15] for n in parse_numbers(r)]
    freq_15 = Counter(all_15)

    # 3. Điểm đánh giá các con số
    candidates = []
    for num in range(100):
        num_str = f"{num:02d}"
        gap = last_seen.get(num_str, 99)
        f_count = freq_15.get(num_str, 0)

        # Loại bỏ lô gan > 9 ngày và lô rơi liên tiếp 3 ngày
        if gap >= 10:
            continue
        if num_str in today_last and num_str in yesterday_last:
            continue

        quality = 0
        # Ưu tiên nhịp rơi đẹp (Gap 2 hoặc 3 ngày)
        if gap in [2, 3]: quality += 12
        elif gap == 1: quality += 7
        elif gap == 4: quality += 5
        
        # Tần suất lý tưởng (3 đến 6 lần trong 15 kỳ)
        if 3 <= f_count <= 6: quality += 8
        elif f_count == 2: quality += 4

        # Ưu tiên số xuất hiện trong giải đặc biệt kỳ gần nhất
        if today_last and num_str == today_last[0]:
            quality += 3

        candidates.append((num_str, quality, f_count))

    # Sắp xếp chọn các con số tối ưu nhất
    candidates.sort(key=lambda x: (x[1], x[2]), reverse=True)
    top_nums = [c[0] for c in candidates[:8]]

    if not top_nums:
        top_nums = ["01", "10", "23", "32"]

    bach_thu = top_nums[0]
    
    # Ghép Xiên 2: Ưu tiên cặp lộn (AB - BA)
    rev_bt = bach_thu[::-1]
    xien_2_pairs = []
    
    if rev_bt != bach_thu and rev_bt in top_nums:
        xien_2_pairs.append([bach_thu, rev_bt])
    else:
        xien_2_pairs.append([bach_thu, top_nums[1] if len(top_nums) > 1 else "00"])

    if len(top_nums) >= 3:
        xien_2_pairs.append([top_nums[1], top_nums[2]])
    else:
        xien_2_pairs.append([top_nums[0], top_nums[1] if len(top_nums) > 1 else "11"])

    xien_3 = top_nums[:3]
    xien_4 = top_nums[:4]

    return {
        'bach_thu': bach_thu,
        'xien_2': xien_2_pairs,
        'xien_3': xien_3,
        'xien_4': xien_4
    }

# --- THUẬT TOÁN ĐỀ (ĐẶC BIỆT): MA TRẬN CHẠM X TỔNG X ĐẦU ĐUÔI ---
def analyze_and_predict_db(results):
    if not results or len(results) < 15:
        return None

    db_history = []
    for r in results[:60]:
        nums = parse_numbers(r)
        if nums:
            db_history.append(nums[0])

    if len(db_history) < 5:
        return None

    last_db = db_history[0]
    if len(last_db) < 2: return None
    
    d1_last, d2_last = last_db[0], last_db[1]

    # 1. BẮT ĐẦU ĐỀ VÀ ĐUÔI ĐỀ NỔI BẬT (3 ĐẦU, 3 ĐUÔI)
    recent_daus = [db[0] for db in db_history[:15] if len(db) == 2]
    recent_duois = [db[1] for db in db_history[:15] if len(db) == 2]

    # Chọn Đầu Đề dựa trên tần suất + bóng âm dương của Đuôi đề kỳ trước
    top_daus = [item[0] for item in Counter(recent_daus).most_common(2)]
    if BONG_DUONG.get(d2_last) not in top_daus:
        top_daus.append(BONG_DUONG.get(d2_last, '0'))
    top_daus = list(dict.fromkeys(top_daus))[:3]

    # Chọn Đuôi Đề dựa trên tần suất + bóng dương của Đầu đề kỳ trước
    top_duois = [item[0] for item in Counter(recent_duois).most_common(2)]
    if BONG_DUONG.get(d1_last) not in top_duois:
        top_duois.append(BONG_DUONG.get(d1_last, '5'))
    top_duois = list(dict.fromkeys(top_duois))[:3]

    # 2. BẮT CHẠM CHỦ LỰC (3 CHẠM)
    recent_10_digits = [d for db in db_history[:10] for d in db if len(db) == 2]
    top_digit = Counter(recent_10_digits).most_common(1)[0][0]

    cham_1 = d2_last
    cham_2 = BONG_DUONG.get(d2_last, '0')
    cham_3 = top_digit

    selected_chams = list(set([cham_1, cham_2, cham_3]))

    # 3. BẮT TỔNG CHỦ LỰC (4 TỔNG)
    tongs = [(int(db[0]) + int(db[1])) % 10 for db in db_history[:20] if len(db) == 2]
    top_tongs = [item[0] for item in Counter(tongs).most_common(4)]

    # 4. DỰNG TẬP HỢP DÀN ĐỀ
    set_10 = set()
    set_20 = set()
    set_36 = set()

    for i in range(100):
        num_str = f"{i:02d}"
        d1, d2 = num_str[0], num_str[1]
        tong = (int(d1) + int(d2)) % 10

        # Dàn 36: Thuộc các Chạm chính HOẶC nằm trong (Đầu chọn x Đuôi chọn) HOẶC Tổng chính
        if (d1 in selected_chams or d2 in selected_chams) or (d1 in top_daus and d2 in top_duois) or (tong in top_tongs):
            set_36.add(num_str)

        # Dàn 20: Chạm chính AND (Tổng chính HOẶC Đầu/Đuôi chọn HOẶC Lộn/Kép)
        if (d1 in selected_chams or d2 in selected_chams):
            if tong in top_tongs or (d1 in top_daus or d2 in top_duois) or d1 == d2 or num_str == (d2_last + d1_last):
                set_20.add(num_str)

        # Dàn 10: Điểm tối ưu cao nhất (Giao giữa Chạm + Tổng + Đầu/Đuôi)
        if (d1 in selected_chams or d2 in selected_chams) and (tong in top_tongs) and (d1 in top_daus or d2 in top_duois):
            set_10.add(num_str)

    # Chuẩn hóa số lượng phần tử
    list_36 = sorted(list(set_36))[:36]
    list_20 = sorted(list(set_20))[:20]
    list_10 = sorted(list(set_10))

    # Bổ sung nếu Dàn 10 chưa đủ 10 số
    if len(list_10) < 10:
        extra_candidates = sorted(list(set_20))
        for ex in extra_candidates:
            if ex not in list_10:
                list_10.append(ex)
            if len(list_10) == 10:
                break
    list_10 = sorted(list_10)[:10]

    return {
        'dau_de': top_daus,
        'duoi_de': top_duois,
        'top_10_db': list_10,
        'top_20_db': list_20,
        'top_36_db': list_36
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
    x2_list = pred['xien_2']
    x3 = pred['xien_3']
    x4 = pred['xien_4']

    x2_hits = [x for x in x2_list if all(num in actual_formatted for num in x)]
    x3_hit = all(num in actual_formatted for num in x3) if len(x3) == 3 and all(num in actual_formatted for num in x3) else False
    x4_hit = all(num in actual_formatted for num in x4) if len(x4) == 4 and all(num in actual_formatted for num in x4) else False

    return {
        'bach_thu': bt,
        'bach_thu_hit': bt in actual_formatted,
        'xien_2': x2_list,
        'xien_2_hits_count': len(x2_hits),
        'xien_3': x3,
        'xien_3_hit': x3_hit,
        'xien_4': x4,
        'xien_4_hit': x4_hit,
        'actual_numbers': actual_formatted
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