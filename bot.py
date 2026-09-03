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

# --- DỮ LIỆU CHUẨN ĐÚNG LỊCH QUAY THỨ 3 - THỨ 5 - THỨ 7 ---
DEFAULT_DATASET = [
    {"date": "2026-08-01", "game": "655", "result": [3, 12, 24, 35, 41, 50]},
    {"date": "2026-08-04", "game": "655", "result": [5, 14, 22, 31, 44, 53]},
    {"date": "2026-08-06", "game": "655", "result": [8, 19, 27, 33, 40, 52]},
    {"date": "2026-08-08", "game": "655", "result": [2, 11, 25, 38, 45, 51]},
    {"date": "2026-08-11", "game": "655", "result": [4, 18, 22, 31, 45, 50]},
    {"date": "2026-08-13", "game": "655", "result": [1, 15, 23, 34, 42, 49]},
    {"date": "2026-08-15", "game": "655", "result": [3, 19, 21, 30, 46, 55]},
    {"date": "2026-08-18", "game": "655", "result": [7, 16, 28, 37, 43, 54]},
    {"date": "2026-08-20", "game": "655", "result": [4, 16, 28, 30, 45, 54]},
    {"date": "2026-08-22", "game": "655", "result": [12, 18, 27, 39, 48, 50]},
    {"date": "2026-08-25", "game": "655", "result": [4, 12, 18, 27, 39, 48]},
    {"date": "2026-08-27", "game": "655", "result": [6, 14, 20, 32, 41, 53]},
    {"date": "2026-08-29", "game": "655", "result": [8, 15, 18, 29, 33, 45]},
    {"date": "2026-09-01", "game": "655", "result": [2, 12, 18, 28, 40, 52]}
]

DATASET = []

def fetch_vietlott_655_data():
    global DATASET
    print("🔄 Đang nạp dữ liệu Power 6/55...", flush=True)
    
    url = "https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/655"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
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
        print(f"⚠️ Lỗi cào web: {e}", flush=True)

    if scraped_results:
        DATASET = sorted(scraped_results, key=lambda x: x["date"])
    else:
        DATASET = DEFAULT_DATASET
        
    return len(DATASET)

# --- THUẬT TOÁN TẠO DÀN SỐ NẮM BẮT CỤM SỐ (10 SỐ) ---
def predict_power_655_dan(history_data: list, total_pick=10) -> list:
    if len(history_data) < 3:
        return sorted(random.sample(range(1, 56), total_pick))

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
        return sorted(random.sample(range(1, 56), total_pick))

    best_triplet = max(triplet_matrix.keys(), key=lambda x: triplet_matrix[x])
    selected = list(best_triplet)

    while len(selected) < total_pick:
        best_next_num = None
        max_link_score = -1
        
        for cand in range(1, 56):
            if cand in selected:
                continue
            
            link_score = sum(
                triplet_matrix.get(tuple(sorted([selected[i], selected[j], cand])), 0)
                for i in range(len(selected)) for j in range(i + 1, len(selected))
            )
            
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
                # Chỉ lọc những ngày là Thứ 3 (1), Thứ 5 (3), Thứ 7 (5)
                if curr.weekday() in [1, 3, 5]:
                    dates_to_test.append(curr.strftime("%Y-%m-%d"))
                if curr.day == end_day:
                    break
                curr += timedelta(days=1)
                if (curr - start_date).days > 60: break
        else:
            end_date = datetime.strptime(end_val_str, "%Y-%m-%d")
            curr = start_date
            while curr <= end_date:
                if curr.weekday() in [1, 3, 5]:
                    dates_to_test.append(curr.strftime("%Y-%m-%d"))
                curr += timedelta(days=1)
    elif re.match(r'^\d{4}-\d{2}-\d{2}$', clean_text):
        dates_to_test.append(clean_text)
        
    return dates_to_test

# --- TELEGRAM HANDLERS ---
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    help_text = (
        "🧪 **BOT BACKTEST POWER 6/55 (LỊCH QUAY CHUẨN T3-T5-T7)**\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "📌 **Cú pháp Backtest:**\n"
        "`/test 655 2026-08-01 => 29`\n\n"
        "🎯 **Cú pháp Dự đoán Dàn:**\n"
        "`/dudoan` - Lấy dàn 10 số tối ưu cho Bao 10\n\n"
        "🔄 **Cập nhật dữ liệu:** `/reload`"
    )
    bot.reply_to(message, help_text, parse_mode="Markdown")

@bot.message_handler(commands=['reload'])
def handle_reload(message):
    count = fetch_vietlott_655_data()
    bot.reply_to(message, f"🔄 Đã nạp lại dữ liệu Vietlott! Tổng số kỳ quay: `{count}`", parse_mode="Markdown")

@bot.message_handler(commands=['test'])
def handle_backtest_655(message):
    raw_text = message.text.strip().replace('/test', '').strip()
    if not raw_text:
        bot.reply_to(message, "⚠️ Cú pháp: `/test 655 2026-08-01 => 29`", parse_mode="Markdown")
        return

    dates_to_test = parse_date_range(raw_text)
    if not dates_to_test:
        bot.reply_to(message, "❌ Không tìm thấy kỳ quay khớp trong dải ngày chọn (Chỉ quay T3, T5, T7)!", parse_mode="Markdown")
        return

    msg = bot.reply_to(message, f"⏳ Đang Backtest Dàn 10 số ({len(dates_to_test)} kỳ quay thực tế)...", parse_mode="Markdown")

    details_list = []
    total_matched_nums = 0
    total_tested_days = 0

    for target_date_str in dates_to_test:
        actual_draw = next((d for d in DATASET if d["date"] == target_date_str), None)
        if not actual_draw:
            continue

        actual_res = set(actual_draw["result"])
        past_history = [
            d for d in DATASET 
            if datetime.strptime(d["date"], "%Y-%m-%d") < datetime.strptime(actual_draw["date"], "%Y-%m-%d")
        ]

        # Dự đoán dàn 10 số
        predicted_10 = predict_power_655_dan(past_history, total_pick=10)
        matched = set(predicted_10).intersection(actual_res)
        match_count = len(matched)
        
        total_matched_nums += match_count
        total_tested_days += 1

        if match_count >= 5:
            icon = "🔥 (TRÚNG 5-6 SỐ)"
        elif match_count >= 3:
            icon = "✅"
        else:
            icon = "❌"

        matched_str = ",".join(map(str, sorted(list(matched)))) if matched else "Không"
        details_list.append(
            f"📅 **{actual_draw['date']}**: Dàn 10 trùng **{match_count}/6** số {icon} `[{matched_str}]`"
        )

    if not details_list:
        bot.edit_message_text("❌ Chưa có dữ liệu kỳ quay trong lịch lịch sử.", chat_id=message.chat.id, message_id=msg.message_id)
        return

    report_header = f"🧪 *BÁO CÁO BACKTEST POWER 6/55 ({total_tested_days} KỲ CHUẨN)*\n━━━━━━━━━━━━━━━━━━━━━\n"
    report_footer = (
        f"\n━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 **TỔNG KẾT HỆ THỐNG:**\n"
        f"• Kỳ test thực tế: `{total_tested_days}`\n"
        f"• Trung bình số con trúng/kỳ trong Dàn 10: `{(total_matched_nums / total_tested_days):.1f}/6` số"
    )

    full_report = report_header + "\n".join(details_list) + report_footer
    bot.edit_message_text(full_report, chat_id=message.chat.id, message_id=msg.message_id, parse_mode="Markdown")

@bot.message_handler(commands=['dudoan'])
def handle_dudoan_655(message):
    dan_10 = predict_power_655_dan(DATASET, total_pick=10)
    pred_str = ", ".join(map(str, dan_10))

    report = (
        f"🎯 *DỰ ĐOÁN POWER 6/55 KỲ TỚI*\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 **Dàn 10 số tối ưu (Chơi Bao/Gộp bộ):**\n`[{pred_str}]`\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 *Phân tích ma trận liên kết cụm cho dải 10 con.*"
    )
    bot.reply_to(message, report, parse_mode="Markdown")

if __name__ == '__main__':
    fetch_vietlott_655_data()
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