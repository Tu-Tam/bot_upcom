import json
import random
from collections import Counter

# --- CẤU HÌNH CÁC GIẢI VIETLOTT ---
GAME_CONFIG = {
    "655": {"name": "Power 6/55", "max_num": 55, "pick": 6, "type": "standard"},
    "645": {"name": "Mega 6/45", "max_num": 45, "pick": 6, "type": "standard"},
    "3d": {"name": "Max 3D", "length": 3, "type": "digit"},
    "keno": {"name": "Keno", "max_num": 80, "pick": 20, "type": "standard"},
}

def parse_numbers(row):
    """Bóc tách và chuẩn hóa dữ liệu danh sách số từ CSDL."""
    if not row:
        return []
    
    raw_nums = []
    if isinstance(row, dict):
        raw_nums = row.get('numbers') or row.get('prizes') or row.get('results') or []
    elif isinstance(row, (list, tuple)):
        raw_nums = row
    elif isinstance(row, str):
        try:
            raw_nums = json.loads(row)
        except Exception:
            raw_nums = row.split(',')

    parsed = []
    for item in raw_nums:
        try:
            parsed.append(int(str(item).strip()))
        except (ValueError, TypeError):
            continue
            
    return parsed

# ==============================================================================
# 1. THUẬT TOÁN DỰ ĐOÁN VIETLOTT
# ==============================================================================
def analyze_and_predict(game_type: str, history_data: list) -> list:
    """
    Phân tích tần suất và nhịp rơi dữ liệu lịch sử để dự đoán số kỳ tới.
    - 6/55 & 6/45: Chọn dàn 6 số xuất hiện nhiều nhất.
    - Keno: Chọn dàn 20 số ưu tiên.
    - Max 3D: Chọn 3 chữ số hàng Trăm, Chục, Đơn vị theo tần suất cao nhất.
    """
    config = GAME_CONFIG.get(game_type)
    if not config:
        return []

    # A. Dự đoán cho Max 3D (Dạng chữ số 0-9)
    if config["type"] == "digit":
        if not history_data:
            return [random.randint(0, 9) for _ in range(config["length"])]

        predicted = []
        for pos in range(config["length"]):
            digits_at_pos = []
            for row in history_data:
                nums = parse_numbers(row)
                if len(nums) > pos:
                    digits_at_pos.append(nums[pos])
            
            if digits_at_pos:
                most_common = Counter(digits_at_pos).most_common(1)[0][0]
                predicted.append(most_common)
            else:
                predicted.append(random.randint(0, 9))
        return predicted

    # B. Dự đoán cho 6/55, 6/45, Keno (Dạng tập hợp số phân biệt)
    all_numbers = []
    for row in history_data[:50]:  # Lấy tối đa 50 kỳ gần nhất làm mẫu
        nums = parse_numbers(row)
        all_numbers.extend(nums)

    if not all_numbers:
        return sorted(random.sample(range(1, config["max_num"] + 1), config["pick"]))

    freq = Counter(all_numbers)
    # Lấy danh sách số có tần suất xuất hiện cao nhất
    top_numbers = [num for num, _ in freq.most_common(config["pick"]) if 1 <= num <= config["max_num"]]

    # Bổ sung số nếu chưa đủ số lượng yêu cầu
    while len(top_numbers) < config["pick"]:
        rand_num = random.randint(1, config["max_num"])
        if rand_num not in top_numbers:
            top_numbers.append(rand_num)

    return sorted(top_numbers)

# ==============================================================================
# 2. HÀM BACKTEST VÀ ĐÁNH GIÁ ĐỘ CHÍNH XÁC
# ==============================================================================
def test_prediction_accuracy(game_type: str, historical_data: list, actual_numbers: list):
    """
    So sánh kết quả dự đoán (dựa trên historical_data) với kết quả thực tế (actual_numbers).
    Trả về chi tiết số trùng khớp và % chính xác.
    """
    if not actual_numbers:
        return None

    config = GAME_CONFIG.get(game_type)
    if not config:
        return None

    actual_formatted = parse_numbers(actual_numbers)
    if not actual_formatted:
        return None

    # Tạo dự đoán dựa trên dữ liệu quá khứ lùi ngày
    predicted = analyze_and_predict(game_type, historical_data)
    if not predicted:
        return None

    # Tính toán kết quả so sánh
    if config["type"] == "digit":
        # Max 3D: So sánh vị trí chính xác
        matched = [p for p, a in zip(predicted, actual_formatted) if p == a]
        matched_count = len(matched)
        total_possible = len(actual_formatted)
    else:
        # 6/55, 6/45, Keno: So sánh giao tập hợp số
        matched = list(set(predicted).intersection(set(actual_formatted)))
        matched_count = len(matched)
        total_possible = len(actual_formatted)

    accuracy_rate = (matched_count / total_possible) * 100 if total_possible > 0 else 0

    return {
        'game_type': game_type,
        'predicted': predicted,
        'actual': actual_formatted,
        'matched': matched,
        'matched_count': matched_count,
        'total_possible': total_possible,
        'accuracy_rate': round(accuracy_rate, 2)
    }
