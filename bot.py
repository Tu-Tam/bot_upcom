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
from bs4 import BeautifulSoup
import numpy as np
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

# --- DỮ LIỆU DỰ PHÒNG CHUẨN KHI KHÔNG CÀO ĐƯỢC WEB ---
DEFAULT_DATASET = [
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
    {"date": "2026-09-01", "game": "655", "result": [2, 12, 18, 28, 40, 52]}
]

DATASET = []

def fetch_vietlott_655_data():
    """Tải dữ liệu Vietlott từ Web scraping, nếu lỗi sẽ nạp Default Dataset."""
    global DATASET
    print("🔄 Đang kiểm tra & nạp dữ liệu Power 6/55...", flush=True)
    
    url = "https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/655"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    scraped_results = []
    try:
        res = requests.get(url, headers=headers, timeout=8)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            rows = soup.select('table.table-hover tbody tr')
            
            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 2:
                    date_raw = cols[0].text.strip()
                    nums_raw = cols[1].find_all('span', class_='ball')
                    if len(nums_raw) >= 6:
                        date_str = datetime.strptime(date_raw, "%d/%m/%Y").strftime("%Y-%m-%d")
                        nums = [int(n.text.strip()) for n in nums_raw[:6]]
                        scraped_results.append({"date": date_str, "game": "655", "result": sorted(nums)})
    except Exception as e:
        print(f"⚠️ Không thể cào dữ liệu từ Web Vietlott: {e}", flush=True)

    if scraped_results:
        DATASET = sorted(scraped_results, key=lambda x: x["date"])
        print(f"✅ Cào thành công {len(DATASET)} kỳ từ Web Vietlott!", flush=True)
    else:
        DATASET = DEFAULT_DATASET
        print(f"✅ Đã nạp thành công bộ dữ liệu cơ sở ({len(DATASET)} kỳ)!", flush=True)
        
    return len(DATASET)

# --- THUẬT TOÁN MA TRẬN TAM GIÁC (SUPER MATRIX) ---
def predict_power_655_super_matrix(history_data: list) -> list:
    if len(history_data) < 3:
        return sorted(random.sample(range(1, 56), 6))

    total_draws = len(history_data)
    weights = np.exp(np.linspace(-2, 0, total_draws))
    
    freq_scores = defaultdict(float)
    triplet_matrix = defaultdict(float)
    
    for idx, draw in enumerate(history_data):
        w = weights[idx]
        res = draw.get("result", [])
        
        for n in res:
            freq_scores[n] += w
            
        for i in range(len(res)):
            for j in range(i + 1, len(res)):
                for k in range(j + 1, len(res)):
                    triplet_key = tuple(sorted([res[i], res[j], res[k]]))
                    triplet_matrix[triplet_key] += w

    if not triplet_matrix:
        return sorted(random.sample(range(1, 56), 6))

    best_triplet = max(triplet_matrix.keys(), key=lambda x: triplet_matrix[x])
    selected = list(best_triplet)

    while len(selected) < 6:
        best_next_num = None
        max_link_score = -1
        
        for cand in range(1, 56):
            if cand in selected:
                continue
            
            link_score = 0
            for i in range(len(selected)):
                for j in range(i + 1, len(selected)):
                    sub_triplet = tuple(sorted([selected[i], selected[j], cand]))
                    link_score += triplet_matrix.get(sub_triplet, 0)
            
            total_cand_score = freq_scores[cand] * 0.8 + link_score * 3.0
            
            if total_cand_score > max_link_score:
                max_link_score = total_cand_score
                best_next_num = cand

        if best_next_num is None:
            remaining = [n for n in range(1, 56) if n not in selected]
            selected.append(random.choice(remaining))
        else:
            selected.append(best_next_num)

    return sorted(selected)

def parse_date_range(raw_input: str) -> list:
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
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    help_text = (
        "🧪 **BOT BACKTEST POWER 6/55**\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "📌 **Cú pháp Backtest:**\n"
        "`/test 655 2026-08-10 => 25`\n\n"
        "🎯 **Cú pháp Dự đoán:**\n"
        "`/dudoan` - Lấy bộ số tối ưu kỳ tới\n\n"
        "🔄 **Cập nhật dữ liệu:**\n"
        "`/reload` - Nạp lại kết quả Vietlott"
    )
    bot.reply_to(message, help_text, parse_mode="Markdown")

@bot.message_handler(commands=['reload'])
def handle_reload(message):
    count = fetch_vietlott_655_data()
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

    msg = bot.reply_to(message, f"⏳ Đang chạy Backtest Super Matrix ({len(dates_to_test)} kỳ)...", parse_mode="Markdown")

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

        predicted_6 = predict_power_655_super_matrix(past_history)
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

    full_report = report_header + "\n\n".join(details_list) + report_footer
    bot.edit_message_text(full_report, chat_id=message.chat.id, message_id=msg.message_id, parse_mode="Markdown")

@bot.message_handler(commands=['dudoan'])
def handle_dudoan_655(message):
    pred = predict_power_655_super_matrix(DATASET)
    pred_str = ", ".join(map(str, pred))

    report = (
        f"🎯 *DỰ ĐOÁN POWER 6/55 KỲ TỚI*\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 **Dàn số tối ưu (Super Matrix):** `[{pred_str}]`\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 *Phân tích Ma trận Tam giác (Triplet Matrix).* "
    )
    bot.reply_to(message, report, parse_mode="Markdown")

if __name__ == '__main__':
    fetch_vietlott_655_data()
    
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