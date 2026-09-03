import os
import sys
import time
import threading
import json
import re
import random
from collections import Counter, defaultdict
from datetime import datetime, timedelta
import requests
import telebot
from flask import Flask

# --- CẤU HÌNH TOKEN & WEB SERVER ---
TOKEN = os.getenv("TELEGRAM_TOKEN")

if not TOKEN:
    print("❌ LỖI FATAL: Chưa cấu hình TELEGRAM_TOKEN!", flush=True)
    sys.exit(1)

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

@app.route('/')
def home():
    return "Vietlott Power 6/55 Bot đang hoạt động!", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# --- BỘ NHỚ LƯU TRỮ DỮ LIỆU TỰ ĐỘNG NẠP ---
DATASET = []

def fetch_vietlott_655_data(limit=100):
    """Tự động nạp kết quả Vietlott Power 6/55 thực tế từ API."""
    global DATASET
    print(f"🔄 Đang nạp dữ liệu Vietlott Power 6/55 ({limit} kỳ gần nhất)...", flush=True)
    
    url = "https://vietlott.vn/api/front/v1/result/power655" # API công khai của Vietlott
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, json={"pageIndex": 0, "pageSize": limit}, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            results = []
            for item in data.get("resultList", []):
                # Ép kiểu dữ liệu ngày YYYY-MM-DD và danh sách 6 số
                date_str = datetime.strptime(item["drawDate"], "%d/%m/%Y").strftime("%Y-%m-%d")
                nums = [int(n) for n in item["result"].split("-")[:6]]
                results.append({"date": date_str, "game": "655", "result": sorted(nums)})
            
            # Sắp xếp theo thứ tự thời gian tăng dần
            DATASET = sorted(results, key=lambda x: x["date"])
            print(f"✅ Đã nạp thành công {len(DATASET)} kỳ quay Vietlott!", flush=True)
            return len(DATASET)
    except Exception as e:
        print(f"⚠️ Lỗi kết nối API Vietlott: {e}. Sử dụng dữ liệu dự phòng.", flush=True)
        
    # Dữ liệu dự phòng nếu mất kết nối API
    if not DATASET:
        DATASET = [
            {"date": "2026-08-10", "game": "655", "result": [12, 15, 23, 34, 41, 52]},
            {"date": "2026-08-12", "game": "655", "result": [4, 18, 22, 31, 45, 50]},
            {"date": "2026-08-15", "game": "655", "result": [3, 19, 21, 30, 46, 55]},
            {"date": "2026-08-20", "game": "655", "result": [4, 16, 28, 30, 45, 54]},
            {"date": "2026-08-22", "game": "655", "result": [12, 18, 27, 39, 48, 50]},
            {"date": "2026-08-25", "game": "655", "result": [4, 12, 18, 27, 39, 48]},
            {"date": "2026-08-29", "game": "655", "result": [8, 15, 18, 29, 33, 45]},
            {"date": "2026-09-01", "game": "655", "result": [2, 12, 18, 28, 40, 52]}
        ]
    return len(DATASET)

# --- THUẬT TOÁN MA TRẬN ĐA TẦNG CAO CẤP ---
def predict_power_655_advanced(history_data: list) -> list:
    """Ma trận Cặp số đi cùng (Co-occurrence) & Phân rã Trọng số thời gian."""
    if len(history_data) < 3:
        return sorted(random.sample(range(1, 56), 6))

    weighted_freq = defaultdict(float)
    co_matrix = defaultdict(lambda: defaultdict(float))
    
    total_draws = len(history_data)
    for idx, draw in enumerate(history_data):
        weight = 1.0 + (idx / total_draws) * 2.0
        res = draw.get("result", [])
        
        for num in res:
            weighted_freq[num] += weight
            
        for i in range(len(res)):
            for j in range(i + 1, len(res)):
                n1, n2 = res[i], res[j]
                co_matrix[n1][n2] += weight
                co_matrix[n2][n1] += weight

    sorted_seeds = sorted(range(1, 56), key=lambda x: weighted_freq[x], reverse=True)
    selected = [sorted_seeds[0]]

    while len(selected) < 6:
        candidate_scores = {}
        for cand in range(1, 56):
            if cand in selected:
                continue
            
            link_score = sum(co_matrix[cand][sel] for sel in selected)
            total_score = weighted_freq[cand] * 1.2 + link_score * 2.5
            candidate_scores[cand] = total_score

        best_cand = max(candidate_scores.keys(), key=lambda x: candidate_scores[x])
        selected.append(best_cand)

    return sorted(selected)

def parse_date_range(raw_input: str) -> list:
    """Cú pháp: 655 YYYY-MM-DD => DD"""
    dates_to_test = []
    clean_text = raw_input.replace('655', '').strip()
    
    range_match = re.search(r'(\d{4}-\d{2}-\d{2})\s*(?:=>|->|-|\s+)\s*(\d{1,2}|\d{4}-\d{2}-\d{2})$', clean_text)
    
    if range_match:
        start_str, end_val_str = range_match.group(1), range_match.group(2)
        start_date = datetime.strptime(start_str, "%Y-%m-%d")
        
        if len(end_val_str) <= 2:
            end_day = int(end_val_str)
            curr = start_date
            while True:
                dates_to_test.append(curr.strftime("%Y-%m-%d"))
                if curr.day == end_day:
                    break
                curr += timedelta(days=1)
                if (curr - start_date).days > 60: break
        else:
            end_date = datetime.strptime(end_val_str, "%Y-%m-%d")
            curr = start_date
            while curr <= end_date:
                dates_to_test.append(curr.strftime("%Y-%m-%d"))
                curr += timedelta(days=1)
    elif re.match(r'^\d{4}-\d{2}-\d{2}$', clean_text):
        dates_to_test.append(clean_text)
        
    return dates_to_test

# --- TELEGRAM HANDLERS ---
@bot.message_handler(commands=['reload'])
def handle_reload(message):
    """Lệnh cập nhật thủ công dữ liệu từ Vietlott."""
    count = fetch_vietlott_655_data(100)
    bot.reply_to(message, f"🔄 Đã cập nhật xong dữ liệu Vietlott! Tổng số kỳ trong bộ nhớ: `{count}`", parse_mode="Markdown")

@bot.message_handler(commands=['test'])
def handle_backtest_655(message):
    raw_text = message.text.strip().replace('/test', '').strip()
    
    if not raw_text:
        bot.reply_to(message, "⚠️ Cú pháp: `/test 655 2026-08-10 => 25`", parse_mode="Markdown")
        return

    dates_to_test = parse_date_range(raw_text)
    if not dates_to_test:
        bot.reply_to(message, "❌ Định dạng ngày không đúng! Dùng: `YYYY-MM-DD => DD`", parse_mode="Markdown")
        return

    msg = bot.reply_to(message, f"⏳ Đang chạy Backtest Ma Trận Đa Tầng ({len(dates_to_test)} kỳ)...", parse_mode="Markdown")

    details_list = []
    total_matched_nums = 0
    total_tested_days = 0

    for target_date_str in dates_to_test:
        try:
            target_date = datetime.strptime(target_date_str, "%Y-%m-%d")
        except ValueError:
            continue

        actual_draw = next((d for d in DATASET if d["date"] == target_date_str), None)
        if not actual_draw:
            future_draws = [d for d in DATASET if datetime.strptime(d["date"], "%Y-%m-%d") >= target_date]
            if future_draws:
                actual_draw = future_draws[0]
            else:
                continue

        actual_res = set(actual_draw["result"])
        
        past_history = [
            d for d in DATASET 
            if datetime.strptime(d["date"], "%Y-%m-%d") < datetime.strptime(actual_draw["date"], "%Y-%m-%d")
        ]

        predicted_6 = predict_power_655_advanced(past_history)
        matched = set(predicted_6).intersection(actual_res)
        match_count = len(matched)
        
        total_matched_nums += match_count
        total_tested_days += 1

        if match_count >= 5:
            icon = "🔥 (JACKPOT)"
        elif match_count >= 3:
            icon = "✅"
        elif match_count >= 1:
            icon = "🥉"
        else:
            icon = "❌"

        matched_str = ",".join(map(str, sorted(list(matched)))) if matched else "Không"
        
        details_list.append(
            f"📅 **{actual_draw['date']}**: Trùng **{match_count}/6** số {icon} `[{matched_str}]`"
        )

    if not details_list:
        bot.edit_message_text("❌ Không có dữ liệu trong dải ngày chọn.", chat_id=message.chat.id, message_id=msg.message_id)
        return

    avg_acc = (total_matched_nums / (total_tested_days * 6)) * 100

    report_header = f"🧪 *BÁO CÁO BACKTEST POWER 6/55 ({total_tested_days} KỲ)*\n━━━━━━━━━━━━━━━━━━━━━\n"
    report_footer = (
        f"\n━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 **TỔNG KẾT HỆ THỐNG:**\n"
        f"• Số kỳ test thành công: `{total_tested_days}`\n"
        f"• Tổng số lượt trùng: `{total_matched_nums}/{total_tested_days * 6}` số\n"
        f"• Độ chính xác trung bình: `{avg_acc:.2f}%`"
    )

    full_report = report_header + "\n".join(details_list) + report_footer
    bot.edit_message_text(full_report, chat_id=message.chat.id, message_id=msg.message_id, parse_mode="Markdown")

@bot.message_handler(commands=['dudoan'])
def handle_dudoan_655(message):
    pred = predict_power_655_advanced(DATASET)
    pred_str = ", ".join(map(str, pred))

    report = (
        f"🎯 *DỰ ĐOÁN POWER 6/55 KỲ TỚI*\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 **Dàn số tối ưu (Ma trận tự động):** `[{pred_str}]`\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 *Phân tích Ma trận Cặp số đi cùng trên dữ liệu thực tế.*"
    )
    bot.reply_to(message, report, parse_mode="Markdown")

# --- LUỒNG CHÍNH ---
if __name__ == '__main__':
    # Nạp dữ liệu Vietlott tự động khi khởi chạy
    fetch_vietlott_655_data(100)
    
    print("🚀 Khởi động Flask & Vietlott Bot...", flush=True)
    threading.Thread(target=run_flask, daemon=True).start()

    try:
        bot.remove_webhook()
        time.sleep(1)
    except Exception as e:
        print(f"⚠️ Webhook warning: {e}", flush=True)

    print("🤖 Bot Telegram đang lắng nghe...", flush=True)
    while True:
        try:
            bot.infinity_polling(skip_pending=True, timeout=20, long_polling_timeout=10)
        except Exception as e:
            print(f"⚠️ Polling retry: {e}", flush=True)
            time.sleep(5)