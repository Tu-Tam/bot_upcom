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
    return "Vietlott Power 6/55 Super Matrix Bot đang hoạt động!", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

DATASET = []

def fetch_vietlott_655_data(limit=300):
    """Tự động nạp 300 kỳ quay gần nhất để đủ không gian mẫu cho Ma trận Tam giác."""
    global DATASET
    print(f"🔄 Đang nạp dữ liệu Vietlott Power 6/55 ({limit} kỳ)...", flush=True)
    
    url = "https://vietlott.vn/api/front/v1/result/power655"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, json={"pageIndex": 0, "pageSize": limit}, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            results = []
            for item in data.get("resultList", []):
                date_str = datetime.strptime(item["drawDate"], "%d/%m/%Y").strftime("%Y-%m-%d")
                nums = [int(n) for n in item["result"].split("-")[:6]]
                results.append({"date": date_str, "game": "655", "result": sorted(nums)})
            
            DATASET = sorted(results, key=lambda x: x["date"])
            print(f"✅ Đã nạp thành công {len(DATASET)} kỳ quay Vietlott!", flush=True)
            return len(DATASET)
    except Exception as e:
        print(f"⚠️ Lỗi kết nối API: {e}", flush=True)
        
    return len(DATASET)

# --- THUẬT TOÁN MÔ HÌNH MA TRẬN TỐI ƯU 5-6 SỐ (SUPER MATRIX) ---
def predict_power_655_super_matrix(history_data: list) -> list:
    if len(history_data) < 5:
        return sorted(random.sample(range(1, 56), 6))

    total_draws = len(history_data)
    
    # 1. Trọng số thời gian (Exponential Decay Weight)
    weights = np.exp(np.linspace(-2, 0, total_draws)) # Kỳ mới nhất trọng số x2.7
    
    freq_scores = defaultdict(float)
    triplet_matrix = defaultdict(float)
    
    for idx, draw in enumerate(history_data):
        w = weights[idx]
        res = draw.get("result", [])
        
        for n in res:
            freq_scores[n] += w
            
        # Tính Ma trận Bộ 3 số hay xuất hiện cùng nhau (Triplet Matrix)
        for i in range(len(res)):
            for j in range(i + 1, len(res)):
                for k in range(j + 1, len(res)):
                    triplet_key = tuple(sorted([res[i], res[j], res[k]]))
                    triplet_matrix[triplet_key] += w

    # 2. Tìm bộ 3 số hạt giống (Seed Triplet) có điểm ma trận cao nhất
    best_triplet = max(triplet_matrix.keys(), key=lambda x: triplet_matrix[x])
    selected = list(best_triplet)

    # 3. Mở rộng bộ 3 thành bộ 6 bằng thuật toán liên kết tối đa (Maximal Linkage)
    while len(selected) < 6:
        best_next_num = None
        max_link_score = -1
        
        for cand in range(1, 56):
            if cand in selected:
                continue
            
            # Tính điểm liên kết của ứng viên với TẤT CẢ các cặp số đã chọn
            link_score = 0
            for i in range(len(selected)):
                for j in range(i + 1, len(selected)):
                    sub_triplet = tuple(sorted([selected[i], selected[j], cand]))
                    link_score += triplet_matrix.get(sub_triplet, 0)
            
            total_cand_score = freq_scores[cand] * 0.8 + link_score * 3.0
            
            if total_cand_score > max_link_score:
                max_link_score = total_cand_score
                best_next_num = cand

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
@bot.message_handler(commands=['reload'])
def handle_reload(message):
    count = fetch_vietlott_655_data(300)
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

    full_report = report_header + "\n".join(details_list) + report_footer
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
        f"💡 *Phân tích Ma trận Tam giác (Triplet Matrix) & Trọng số Muộn.*"
    )
    bot.reply_to(message, report, parse_mode="Markdown")

if __name__ == '__main__':
    fetch_vietlott_655_data(300)
    
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