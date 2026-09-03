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
    return "Vietlott Power 6/55 Bot đang hoạt động!", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# --- CSDL MẪU LỊCH SỬ POWER 6/55 (1-55) ---
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

# --- THUẬT TOÁN SOI CẦU DÀN 6 SỐ POWER 6/55 ---
def predict_power_655(history_data: list) -> list:
    """Tối ưu dự đoán 6 số bằng Phân tích Tần suất + Cân bằng Chẵn/Lẻ + Độ gan."""
    if len(history_data) < 3:
        return sorted(random.sample(range(1, 56), 6))

    all_numbers = [num for draw in history_data for num in draw.get("result", [])]
    freq = Counter(all_numbers)

    # Tính nhịp gan (kỳ gần nhất xuất hiện)
    last_seen = {}
    total_draws = len(history_data)
    for idx, draw in enumerate(reversed(history_data)):
        for num in draw.get("result", []):
            if num not in last_seen:
                last_seen[num] = idx

    # Trọng số điểm
    scores = {}
    for n in range(1, 56):
        f_score = freq.get(n, 0) * 2.5
        g_score = last_seen.get(n, total_draws) * 1.0
        scores[n] = f_score + g_score

    ranked = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

    # Cân bằng Chẵn / Lẻ (Lấy tối đa 4 chẵn hoặc 4 lẻ)
    selected = []
    even_cnt, odd_cnt = 0, 0
    for num in ranked:
        if len(selected) == 6:
            break
        if num % 2 == 0 and even_cnt < 4:
            selected.append(num)
            even_cnt += 1
        elif num % 2 != 0 and odd_cnt < 4:
            selected.append(num)
            odd_cnt += 1

    while len(selected) < 6:
        for num in ranked:
            if num not in selected:
                selected.append(num)
                break

    return sorted(selected)

def parse_date_range(raw_input: str) -> list:
    """Xử lý cú pháp: 655 YYYY-MM-DD => DD hoặc YYYY-MM-DD => DD"""
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

# --- HANDLER LỆNH TELEGRAM ---
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

    msg = bot.reply_to(message, f"⏳ Đang thực hiện Backtest Power 6/55 ({len(dates_to_test)} kỳ)...", parse_mode="Markdown")

    details_list = []
    total_matched_nums = 0
    total_tested_days = 0

    for target_date_str in dates_to_test:
        try:
            target_date = datetime.strptime(target_date_str, "%Y-%m-%d")
        except ValueError:
            continue

        # Tìm kỳ quay trùng ngày hoặc kỳ kế tiếp
        actual_draw = next((d for d in DATASET if d["date"] == target_date_str), None)
        if not actual_draw:
            future_draws = [d for d in DATASET if datetime.strptime(d["date"], "%Y-%m-%d") >= target_date]
            if future_draws:
                actual_draw = future_draws[0]
            else:
                continue

        actual_res = set(actual_draw["result"])
        
        # Lấy dữ liệu trước ngày test để dự đoán
        past_history = [
            d for d in DATASET 
            if datetime.strptime(d["date"], "%Y-%m-%d") < datetime.strptime(actual_draw["date"], "%Y-%m-%d")
        ]

        # Dự đoán 6 số
        predicted_6 = predict_power_655(past_history)
        
        # So sánh kết quả
        matched = set(predicted_6).intersection(actual_res)
        match_count = len(matched)
        
        total_matched_nums += match_count
        total_tested_days += 1

        icon = "✅" if match_count >= 3 else ("🥉" if match_count >= 1 else "❌")
        matched_str = ",".join(map(str, sorted(list(matched)))) if matched else "Không"
        
        details_list.append(
            f"📅 **{actual_draw['date']}**: Trùng **{match_count}/6** số {icon} `[{matched_str}]`"
        )

    if not details_list:
        bot.edit_message_text("❌ Không có dữ liệu trong dải ngày bạn chọn.", chat_id=message.chat.id, message_id=msg.message_id)
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

@bot.message_handler(commands=['dudoan', 'test655'])
def handle_dudoan_655(message):
    pred = predict_power_655(DATASET)
    pred_str = ", ".join(map(str, pred))

    report = (
        f"🎯 *DỰ ĐOÁN POWER 6/55 KỲ TỚI*\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 **Dàn số tối ưu:** `[{pred_str}]`\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 *Phân tích Ma trận Trọng số Đa tầng & Cân bằng Chẵn/Lẻ.*"
    )
    bot.reply_to(message, report, parse_mode="Markdown")

# --- LUỒNG CHÍNH ---
if __name__ == '__main__':
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