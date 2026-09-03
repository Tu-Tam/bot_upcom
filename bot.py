import os
import sys
import time
import threading
import json
import re
import random
from collections import Counter
from datetime import datetime, timedelta
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
    return "Vietlott Power 6/55 Wheel System Bot đang hoạt động!", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# --- CSDL LỊCH SỬ POWER 6/55 ---
DATASET = [
    {"date": "2026-08-10", "game": "655", "result": [12, 15, 23, 34, 41, 52]},
    {"date": "2026-08-11", "game": "655", "result": [4, 18, 22, 31, 45, 50]},
    {"date": "2026-08-12", "game": "655", "result": [9, 14, 27, 36, 42, 53]},
    {"date": "2026-08-13", "game": "655", "result": [1, 11, 25, 33, 40, 49]},
    {"date": "2026-08-14", "game": "655", "result": [8, 16, 29, 37, 44, 51]},
    {"date": "2026-08-15", "game": "655", "result": [3, 19, 21, 30, 46, 55]},
    {"date": "2026-08-16", "game": "655", "result": [7, 13, 28, 35, 43, 48]},
    {"date": "2026-08-17", "game": "655", "result": [1, 17, 24, 32, 39, 54]},
    {"date": "2026-08-18", "game": "655", "result": [5, 10, 26, 38, 47, 52]},
    {"date": "2026-08-19", "game": "655", "result": [6, 20, 35, 41, 49, 53]},
    {"date": "2026-08-20", "game": "655", "result": [4, 16, 28, 30, 45, 54]},
    {"date": "2026-08-21", "game": "655", "result": [2, 15, 23, 34, 43, 51]},
    {"date": "2026-08-22", "game": "655", "result": [12, 18, 27, 39, 48, 50]},
    {"date": "2026-08-23", "game": "655", "result": [8, 14, 25, 31, 42, 49]},
    {"date": "2026-08-24", "game": "655", "result": [4, 19, 22, 26, 44, 54]},
    {"date": "2026-08-25", "game": "655", "result": [4, 12, 18, 27, 39, 48]},
    {"date": "2026-08-29", "game": "655", "result": [8, 15, 18, 29, 33, 45]},
    {"date": "2026-09-01", "game": "655", "result": [2, 12, 18, 28, 40, 52]},
]

# --- THUẬT TOÁN MA TRẬN TỐI ƯU 5-6 SỐ ---
def generate_wheel_core(history_data: list, pool_size=14) -> list:
    """Tạo Dàn Core (Pool) gồm 12-14 số tiềm năng nhất."""
    if len(history_data) < 3:
        return sorted(random.sample(range(1, 56), pool_size))

    all_numbers = [num for draw in history_data for num in draw.get("result", [])]
    freq = Counter(all_numbers)

    last_seen = {}
    total_draws = len(history_data)
    for idx, draw in enumerate(reversed(history_data)):
        for num in draw.get("result", []):
            if num not in last_seen:
                last_seen[num] = idx

    # Tính ma trận trọng số tối ưu
    scores = {}
    for n in range(1, 56):
        # Kết hợp Tần suất + Độ gan rơi đúng nhịp (3-7 kỳ) + Điểm lặp lại
        f_score = freq.get(n, 0) * 3.0
        g_val = last_seen.get(n, total_draws)
        g_score = 5.0 if 2 <= g_val <= 6 else (2.0 if g_val < 2 else 1.0)
        scores[n] = f_score + g_score

    ranked = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
    return ranked[:pool_size]

def predict_optimized_combination(history_data: list) -> list:
    """Lọc bộ 6 số tối ưu nhất từ Dàn Core thông qua Bộ Lọc Điều Kiện Toán Học."""
    core_pool = generate_wheel_core(history_data, pool_size=14)
    
    best_combo = None
    best_score = -1

    # Duyệt ngẫu nhiên tổ hợp từ Core Pool để tìm bộ lọc đạt chuẩn cao nhất
    for _ in range(500):
        combo = sorted(random.sample(core_pool, 6))
        
        # 1. Bộ lọc Tổng (Sum Filter: 120 - 210)
        total_sum = sum(combo)
        if not (120 <= total_sum <= 210):
            continue
            
        # 2. Bộ lọc Chẵn / Lẻ (Tỷ lệ 3:3 hoặc 4:2)
        evens = sum(1 for n in combo if n % 2 == 0)
        if evens < 2 or evens > 4:
            continue

        # 3. Bộ lọc Khoảng (Đầu số phân bổ ít nhất 3 dải hàng chục)
        decades = set(n // 10 for n in combo)
        if len(decades) < 3:
            continue

        # Điểm số của bộ hợp lệ
        combo_score = total_sum
        if combo_score > best_score:
            best_score = combo_score
            best_combo = combo

    if not best_combo:
        best_combo = sorted(random.sample(core_pool, 6))

    return best_combo

def parse_date_range(raw_input: str) -> list:
    """Xử lý dải ngày test: 655 YYYY-MM-DD => DD"""
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

# --- HANDLER BÁO CÁO TELEGRAM ---
@bot.message_handler(commands=['test'])
def handle_backtest_655(message):
    raw_text = message.text.strip().replace('/test', '').strip()
    
    if not raw_text:
        bot.reply_to(message, "⚠️ Cú pháp: `/test 655 2026-08-10 => 25`", parse_mode="Markdown")
        return

    dates_to_test = parse_date_range(raw_text)
    if not dates_to_test:
        bot.reply_to(message, "❌ Cú pháp sai! Dùng: `YYYY-MM-DD => DD`", parse_mode="Markdown")
        return

    msg = bot.reply_to(message, f"⏳ Đang chạy Backtest Ma Trận Xoay Power 6/55 ({len(dates_to_test)} kỳ)...", parse_mode="Markdown")

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

        # Dự đoán theo Ma trận Xoay Lọc Tối Ưu
        predicted_6 = predict_optimized_combination(past_history)
        
        matched = set(predicted_6).intersection(actual_res)
        match_count = len(matched)
        
        total_matched_nums += match_count
        total_tested_days += 1

        # Ký hiệu giải thưởng
        if match_count >= 5:
            icon = "🔥 (TRÚNG LỚN)"
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
        bot.edit_message_text("❌ Không có dữ liệu phù hợp.", chat_id=message.chat.id, message_id=msg.message_id)
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

    full_report = report_header + "\n\n".join(details_list) + report_footer
    bot.edit_message_text(full_report, chat_id=message.chat.id, message_id=msg.message_id, parse_mode="Markdown")

@bot.message_handler(commands=['dudoan'])
def handle_dudoan_655(message):
    pred = predict_optimized_combination(DATASET)
    core = generate_wheel_core(DATASET, pool_size=12)
    
    pred_str = ", ".join(map(str, pred))
    core_str = ", ".join(map(str, sorted(core)))

    report = (
        f"🎯 *DỰ ĐOÁN POWER 6/55 KỲ TỚI*\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 **Bộ 6 số tối ưu nhất:** `[{pred_str}]`\n"
        f"📦 **Dàn Core lót (12 số):** `[{core_str}]`\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 *Thuật toán Ma trận Xoay Wheel System & Bộ lọc Toán học Sum/Parity.*"
    )
    bot.reply_to(message, report, parse_mode="Markdown")

if __name__ == '__main__':
    print("🚀 Khởi động Vietlott Bot...", flush=True)
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