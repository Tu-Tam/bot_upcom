import json
import os
import re
from vietlott_scraper import fetch_vietlott_655_data, get_dataset
from analytics import predict_power_655_hybrid_10

DATA_FILE = "vietlott_655.json"

def parse_test_params(param_str: str):
    """
    Phân tích chuỗi tham số truyền vào từ Telegram.
    Ví dụ: '2026-08-01 => 20' hoặc '2026-08-01 20' hoặc '2026-08-01'
    """
    # Tìm ngày YYYY-MM-DD
    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', param_str)
    start_date = date_match.group(1) if date_match else "2026-08-01"
    
    # Tìm số lượng kỳ quay đằng sau
    num_draws = 30 # Mặc định
    number_match = re.search(r'(?:=>|\s+)(\d+)\s*$', param_str)
    if number_match:
        num_draws = int(number_match.group(1))

    return start_date, num_draws

def run_backtest_655(raw_args: str):
    start_date_str, num_draws = parse_test_params(raw_args)
    
    # 1. Lấy dữ liệu
    data = get_dataset()
    if not data:
        data = fetch_vietlott_655_data(limit=200)

    if not data:
        return "❌ Không thể tải dữ liệu lịch sử Vietlott."

    # 2. Lọc các kỳ quay từ start_date_str
    future_draws = [d for d in data if d["date"] >= start_date_str]

    if not future_draws:
        return f"❌ Không tìm thấy dữ liệu kỳ quay phù hợp sau ngày {start_date_str}."

    # Lấy đúng N kỳ quay theo yêu cầu (20 hoặc 29 kỳ)
    test_draws = future_draws[:num_draws]
    results_log = []
    total_matches = 0

    for draw in test_draws:
        target_date = draw["date"]
        actual_result = set(draw["result"])

        # Lấy lịch sử tính đến trước ngày target
        history_until_now = [d for d in data if d["date"] < target_date]
        
        if not history_until_now:
            continue

        predicted_10 = predict_power_655_hybrid_10(history_until_now)
        
        matched = set(predicted_10).intersection(actual_result)
        match_count = len(matched)
        total_matches += match_count
        
        status = "✅" if match_count >= 3 else "❌"
        matched_str = ",".join(map(str, sorted(list(matched))))
        results_log.append(f"📅 {target_date}: Trùng {match_count}/6 {status} [{matched_str}]")

    avg_matches = total_matches / len(test_draws) if test_draws else 0
    
    response = f"🧪 BACKTEST HYBRID ({len(test_draws)} KỲ)\n"
    response += "\n".join(results_log)
    response += f"\n\n📊 TB: {avg_matches:.1f}/6 số"
    
    return response