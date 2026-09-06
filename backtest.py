import json
import os
from datetime import datetime
from vietlott_scraper import fetch_and_update_vietlott_655
from analytics import predict_power_655_hybrid_10

DATA_FILE = "vietlott_655.json"

def load_data():
    if not os.path.exists(DATA_FILE) or os.path.getsize(DATA_FILE) == 0:
        return fetch_and_update_vietlott_655()
    
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not data:
                return fetch_and_update_vietlott_655()
            return data
    except Exception:
        return fetch_and_update_vietlott_655()

def run_backtest(start_date_str, num_draws=30):
    data = load_data()
    if not data:
        return "❌ Không thể tải dữ liệu lịch sử Vietlott."

    # Lọc danh sách kỳ quay từ ngày bắt đầu
    future_draws = [d for d in data if d["date"] >= start_date_str]
    
    if not future_draws:
        # Nếu không có ngày lớn hơn, thử làm mới dữ liệu
        data = fetch_and_update_vietlott_655()
        future_draws = [d for d in data if d["date"] >= start_date_str]

    if not future_draws:
        return f"❌ Không tìm thấy dữ liệu kỳ quay phù hợp sau ngày {start_date_str}."

    test_draws = future_draws[:num_draws]
    results_log = []
    total_matches = 0

    for draw in test_draws:
        target_date = draw["date"]
        actual_result = set(draw["result"])

        # Tập dữ liệu quá khứ tính đến trước ngày target
        history_until_now = [d for d in data if d["date"] < target_date]
        
        if not history_until_now:
            continue

        # Gọi dự đoán dàn 10 số
        predicted_10 = predict_power_655_hybrid_10(history_until_now)
        
        # So khớp
        matched = set(predicted_10).intersection(actual_result)
        match_count = len(matched)
        total_matches += match_count
        
        status = "✅" if match_count >= 3 else "❌"
        matched_str = ",".join(map(str, sorted(list(matched))))
        results_log.append(f"📅 {target_date}: Trùng {match_count}/6 {status} [{matched_str}]")

    avg_matches = total_matches / len(test_draws) if test_draws else 0
    
    response = f"🧪 BACKTEST HYBRID ({len(test_draws)} KỲ)\n"
    response += "\n\n".join(results_log)
    response += f"\n\n📊 TB: {avg_matches:.1f}/6 số"
    
    return response