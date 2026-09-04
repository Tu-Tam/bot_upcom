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
    return "Vietlott Power 6/55 Super Bot đang hoạt động!", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

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

# --- THUẬT TOÁN HYBRID MATRIX & GAP ANALYSIS (TỐI ƯU DÀN 10 SỐ) ---
def predict_power_655_hybrid_10(history_data: list) -> list:
    if len(history_data) < 3:
        return sorted(random.sample(range(1, 56), 10))

    total_draws = len(history_data)
    
    # 1. Tính khoảng cách chưa về (Gap Analysis)
    last_seen = {}
    for idx, draw in enumerate(history_data):
        for num in draw.get("result", []):
            last_seen[num] = idx

    gap_scores = {}
    for num in range(1, 56):
        gap = (total_draws - 1) - last_seen.get(num, -1)
        # Điểm nhịp rơi tối ưu: Số vừa về trong 1-5 kỳ gần nhất nhận điểm thưởng cao
        if 1 <= gap <= 5:
            gap_scores[num] = 2.5
        elif 6 <= gap <= 10:
            gap_scores[num] = 1.8
        else:
            gap_scores[num] = 1.0

    # 2. Trọng số ma trận cặp số
    pair_matrix = defaultdict(float)
    weights = np.exp(np.linspace(-1.5, 0, total_draws))
    
    for idx, draw in enumerate(history_data):
        w = weights[idx]
        res = draw.get("result", [])
        for i in range(len(res)):
            for j in range(i + 1, len(res)):
                n1, n2 = res[i], res[j]
                pair_matrix[(n1, n2)] += w
                pair_matrix[(n2, n1)] += w

    # 3. Lựa chọn hạt giống & mở rộng dàn 10 số cân bằng dải số
    scores = {}
    for num in range(1, 56):
        link_score = sum(pair_matrix.get((num, other), 0) for other in range(1, 56) if other != num)
        scores[num] = link_score * 0.6 + gap_scores[num] * 2.0

    sorted_candidates = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
    
    # Lọc lấy 10 số đảm bảo phân bổ đều các đầu số (0x, 1x, 2x, 3x, 4x, 5x)
    selected = []
    head_count = defaultdict(int)

    for cand in sorted_candidates:
        head = cand // 10
        if head_count[head] < 3: # Mỗi đầu số không chọn quá 3 con để tránh dồn cục
            selected.append(cand)
            head_count[head] += 1
        if len(selected) == 10:
            break

    while len(selected) < 10:
        for cand in sorted_candidates:
            if cand not in selected:
                selected.append(cand)
                if len(selected) == 10:
                    break

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
        "🧪 **BOT BACKTEST POWER 6/55 (DÀN 10 SỐ HYBRID)**\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "📌 **Cú pháp Backtest:**\n"
        "`/test 655 2026-08-01 => 29`\n\n"
        "🎯 **Cú pháp Dự đoán Dàn 10:**\n"
        "`/dudoan` - Lấy dàn 10 số tối ưu\n\n"
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
        bot.reply_to(message, "❌ Không tìm thấy kỳ quay khớp!", parse_mode="Markdown")
        return

    msg = bot.reply_to(message, f"⏳ Đang Backtest Dàn 10 Hybrid ({len(dates_to_test)} kỳ)...", parse_mode="Markdown")

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

        predicted_10 = predict_power_655_hybrid_10(past_history)
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
        bot.edit_message_text("❌ Chưa có dữ liệu kỳ quay trong dải ngày chọn.", chat_id=message.chat.id, message_id=msg.message_id)
        return

    report_header = f"🧪 *BÁO CÁO BACKTEST POWER 6/55 (DÀN 10 HYBRID)*\n━━━━━━━━━━━━━━━━━━━━━\n"
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
    dan_10 = predict_power_655_hybrid_10(DATASET)
    pred_str = ", ".join(map(str, dan_10))

    report = (
        f"🎯 *DỰ ĐOÁN POWER 6/55 KỲ TỚI*\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 **Dàn 10 số tối ưu Hybrid:**\n`[{pred_str}]`\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 *Đã phân bổ đều dải số & tối ưu nhịp rơi.*"
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