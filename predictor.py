import json
from collections import Counter

def extract_prize_details(row):
    """
    Phân tách chi tiết từng giải từ CSDL để tính trọng số vị trí và soi cầu kẹp.
    """
    raw_prizes = row.get('raw_prizes') or row.get('prizes') or row.get('results')
    
    # Trường hợp 1: Dữ liệu dạng Dict chứa các giải
    if isinstance(raw_prizes, dict):
        return raw_prizes
    
    # Trường hợp 2: Dữ liệu dạng Chuỗi JSON
    if isinstance(raw_prizes, str):
        try:
            parsed = json.loads(raw_prizes)
            if isinstance(parsed, dict):
                return parsed
        except:
            pass

    # Trường hợp 3: Fallback từ danh sách 27 con lô phẳng
    nums = row.get('numbers', [])
    if isinstance(nums, str):
        try: nums = json.loads(nums)
        except: nums = nums.split(',')
    nums = [str(n).zfill(2)[-2:] for n in nums if str(n).strip()]

    if len(nums) >= 27:
        return {
            'db': [nums[0]],
            'g1': [nums[1]],
            'g2': nums[2:4],
            'g3': nums[4:10],
            'g4': nums[10:14],
            'g5': nums[14:20],
            'g6': nums[20:23],
            'g7': nums[23:27]
        }
    return {'all': nums}

def find_sandwich_numbers(row):
    """
    Soi cầu kẹp (Sandwich pattern) ở các giải 4-5 chữ số.
    Ví dụ: Giải Nhất ra 58825 -> Con 88 hoặc 82 bị kẹp.
    """
    sandwiches = []
    prizes = extract_prize_details(row)
    
    for p_list in prizes.values():
        if isinstance(p_list, list):
            for item in p_list:
                s = str(item).strip()
                if len(s) in [4, 5]:
                    # Dạng A-XX-A (Ví dụ: 1231 -> 23)
                    if s[0] == s[-1]:
                        sandwiches.append(s[1:-1][-2:].zfill(2))
                    # Dạng AB-X-AB hoặc lấy 2 số giữa giải 5 chữ số (ABCDE -> BC, CD)
                    elif len(s) == 5:
                        sandwiches.append(s[1:3])
                        sandwiches.append(s[2:4])
    return sandwiches

# --- THUẬT TOÁN DỰ ĐOÁN LÔ TÔ (PHÂN TÍCH ALL GIẢI) ---
def analyze_and_predict(results):
    if not results or len(results) < 10:
        return None

    data_100 = results[:100]
    recent_3 = results[:3]
    today_last = results[0]

    # 1. Tính điểm vị trí từng giải cho 10 kỳ gần nhất
    scores = {f"{i:02d}": 0.0 for i in range(100)}

    for idx, r in enumerate(data_100[:10]):
        prizes = extract_prize_details(r)
        weight_decay = 1.0 / (idx + 1) # Ngày càng gần điểm càng cao

        for p_name, p_val in prizes.items():
            if not isinstance(p_val, list): continue
            
            # Phân trọng số theo thứ hạng Giải
            p_weight = 1.0
            if 'db' in p_name.lower(): p_weight = 2.5
            elif 'g1' in p_name.lower(): p_weight = 2.0
            elif 'g2' in p_name.lower() or 'g3' in p_name.lower(): p_weight = 1.5

            for num in p_val:
                num_str = str(num).zfill(2)[-2:]
                if num_str.isdigit():
                    scores[num_str] += (p_weight * weight_decay * 2.0)

    # 2. Thống kê tần suất 100 kỳ (Nền tảng)
    all_100 = []
    for r in data_100:
        p = extract_prize_details(r)
        for v in p.values():
            if isinstance(v, list):
                all_100.extend([str(x).zfill(2)[-2:] for x in v if str(x).isdigit()])
    freq_100 = Counter(all_100)

    for num_str in scores:
        scores[num_str] += freq_100.get(num_str, 0) * 0.8

    # 3. Phân tích Cầu Kẹp kỳ vừa ra (+4.0 điểm)
    sandwich_nums = find_sandwich_numbers(today_last)
    for s_num in sandwich_nums:
        if s_num in scores:
            scores[s_num] += 4.0

    # 4. Phạt nhẹ lô rơi bệt 3 ngày liên tiếp
    last_3_nums = []
    for r in recent_3:
        p = extract_prize_details(r)
        for v in p.values():
            if isinstance(v, list):
                last_3_nums.extend([str(x).zfill(2)[-2:] for x in v if str(x).isdigit()])
    
    freq_3 = Counter(last_3_nums)
    for num_str, count in freq_3.items():
        if count >= 3 and num_str in scores:
            scores[num_str] *= 0.75 # Trừ 25% điểm nếu đã ra quá nhiều

    # 5. Sắp xếp & Chọn Lô
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    top_candidates = [item[0] for item in ranked]

    # Kẹp cặp lộn thông minh vào Top 5/Top 10
    final_top = []
    for num in top_candidates:
        if num not in final_top:
            final_top.append(num)
        
        pair = num[1] + num[0]
        if pair not in final_top and len(final_top) < 10:
            if top_candidates.index(num) < 4:
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

# --- THUẬT TOÁN DỰ ĐOÁN GIẢI ĐẶC BIỆT ---
def analyze_and_predict_db(results):
    if not results or len(results) < 10:
        return None

    recent_30 = results[:30]
    db_list = []
    for r in recent_30:
        prizes = extract_prize_details(r)
        db_val = prizes.get('db', [])
        if db_val:
            db_list.append(str(db_val[0]).zfill(2)[-2:])

    if not db_list:
        return None

    chams = []
    tongs = []
    for db in db_list:
        if len(db) >= 2 and db.isdigit():
            d1, d2 = int(db[0]), int(db[1])
            chams.extend([d1, d2])
            tongs.append((d1 + d2) % 10)

    top_chams = [item[0] for item in Counter(chams).most_common(5)]
    top_tongs = [item[0] for item in Counter(tongs).most_common(5)]

    dan_36, dan_20, dan_10 = [], [], []

    for i in range(100):
        num_str = f"{i:02d}"
        d1, d2 = int(num_str[0]), int(num_str[1])
        tong = (d1 + d2) % 10

        if d1 in top_chams or d2 in top_chams or tong in top_tongs:
            dan_36.append(num_str)

    for num_str in dan_36:
        d1, d2 = int(num_str[0]), int(num_str[1])
        tong = (d1 + d2) % 10
        if (d1 in top_chams[:3] or d2 in top_chams[:3]) and (tong in top_tongs[:4]):
            dan_20.append(num_str)

    for num_str in dan_20:
        d1, d2 = int(num_str[0]), int(num_str[1])
        tong = (d1 + d2) % 10
        if (d1 in top_chams[:2] or d2 in top_chams[:2]) and (tong in top_tongs[:3]):
            dan_10.append(num_str)

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

    if isinstance(actual_numbers, dict):
        flat_nums = []
        for v in actual_numbers.values():
            if isinstance(v, list): flat_nums.extend(v)
        actual_formatted = [str(n).zfill(2)[-2:] for n in flat_nums]
    else:
        actual_formatted = [str(n).zfill(2)[-2:] for n in actual_numbers]

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

    if isinstance(actual_numbers, dict):
        actual_db = str(actual_numbers.get('db', [''])[0]).zfill(2)[-2:]
    else:
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