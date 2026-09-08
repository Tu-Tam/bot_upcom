import os
import re
import threading
from flask import Flask
import telebot
from collections import Counter
import random
from vietlott_scraper import fetch_vietlott_655_data, fetch_vietlott_645_data, get_dataset

# -------------------------------------------------------------
# 1. WEB SERVER CHỐNG SẬP RENDER
# -------------------------------------------------------------
app = Flask(__name__)

@app.route('/')
def home():
    return "Vietlott Bot Status: OK"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

flask_thread = threading.Thread(target=run_flask)
flask_thread.daemon = True
flask_thread.start()

# -------------------------------------------------------------
# 2. KHỞI TẠO TELEGRAM BOT
# -------------------------------------------------------------
TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
bot = telebot.TeleBot(TOKEN)

def generate_v5_max_matrix(history_data: list, game="655", num_combos=80) -> list:
    """
    Thuật toán V5: Mở rộng Ma trận Top 30 số & Sinh Dàn 80 bộ 
    để tối đa hóa khả năng trúng 5-6 số trong chuỗi Backtest.
    """
    if len(history_data) < 10:
        return [[1, 2, 3, 4, 5, 6]]

    is_655 = (str(game) == "655")
    max_num = 55 if is_655 else 45
    top_n_matrix = 35 if is_655 else 30  # Mở rộng ma trận phủ

    recent_draws = [d["result"] for d in history_data[-70:]] # Phân tích 70 kỳ gần nhất

    # 1. Thống kê Tần suất
    flat_nums = [n for draw in recent_draws for n in draw]
    freq = Counter(flat_nums)

    # 2. Thống kê Chu kỳ Gan (Số kỳ chưa về)
    last_seen = {}
    for idx, draw in enumerate(reversed(recent_draws)):
        for n in draw:
            if n not in last_seen:
                last_seen[n] = idx

    # 3. Chấm điểm Trọng số V5
    scores = {}
    for n in range(1, max_num + 1):
        f_score = freq.get(n, 0) / len(recent_draws)
        r_score = last_seen.get(n, 70)
        
        # Kết hợp tần suất nóng và chu kỳ điểm rơi
        scores[n] = (f_score * 0.45) + ((1 / (r_score + 1)) * 0.35) + (random.uniform(0.01, 0.05))

    # 4. Lấy Ma trận rộng Top 30-35 số
    top_candidates = sorted(scores, key=scores.get, reverse=True)[:top_n_matrix]

    # 5. Sinh Dàn 80 bộ số phủ Ma trận
    combos = []
    random.seed(len(history_data))
    
    attempts = 0
    while len(combos) < num_combos and attempts < 2500:
        attempts += 1
        combo = sorted(random.sample(top_candidates, 6))
        
        # Điều kiện 1: Tỷ lệ Chẵn/Lẻ (2/4, 3/3, 4/2)
        evens = sum(1 for x in combo if x % 2 == 0)
        if evens < 2 or evens > 4:
            continue
            
        # Điều kiện 2: Tổng dãy số
        total_sum = sum(combo)
        min_s = 80 if is_655 else 65
        max_s = 235 if is_655 else 195
        if not (min_s <= total_sum <= max_s):
            continue

        if combo not in combos:
            combos.append(combo)

    return combos if combos else [top_candidates[:6]]

def parse_date_range(raw_text: str, dataset: list) -> list:
    clean_text = re.sub(r'^(655|645)', '', raw_text).strip()
    match = re.search(r'(\d{4}-\d{2}-\d{2})\s*(?:=>|->|-|\s+)\s*(\d{1,3}|\d{4}-\d{2}-\d{2})$', clean_text)
    
    sorted_dataset = sorted(dataset, key=lambda x: x["date"])
    
    if not match:
        single_date = re.search(r'(\d{4}-\d{2}-\d{2})', clean_text)
        if single_date:
            dt_str = single_date.group(1)
            return [d["date"] for d in sorted_dataset if d["date"] == dt_str]
        return []

    start_str, end_val = match.group(1), match.group(2)
    future_draws = [d["date"] for d in sorted_dataset if d["date"] >= start_str]
    
    if not future_draws:
        if end_val.isdigit():
            return [d["date"] for d in sorted_dataset[-int(end_val):]]
        return []

    if end_val.isdigit():
        return future_draws[:int(end_val)]
    else:
        return [dt for dt in future_draws if dt <= end_val]

@bot.message_handler(commands=['reload'])
def handle_reload(message):
    bot.reply_to(message, "⏳ Đang cào dữ liệu mới từ Vietlott, vui lòng chờ...")
    data_655 = fetch_vietlott_655_data(300)
    data_645 = fetch_vietlott_645_data(300)
    
    msg = f"🔄 Đã cập nhật CSDL:\n- Power 6/55: {len(data_655)} kỳ\n\n- Mega 6/45: {len(data_645)} kỳ"
    bot.send_message(message.chat.id, msg)

@bot.message_handler(commands=['test'])
def handle_test(message):
    args = message.text.replace('/test', '').strip()
    game = "645" if "645" in args else "655"
    
    dataset = get_dataset(game)
    dates = parse_date_range(args, dataset)
    
    if not dates:
        bot.reply_to(message, "❌ Không tìm thấy kỳ quay phù hợp!")
        return

    data_map = {d["date"]: d["result"] for d in dataset}
    sorted_dataset = sorted(dataset, key=lambda x: x["date"])
    
    total_max_match = 0
    lines = [f"🧪 BACKTEST MATRIX V5 {game} - DÀN 80 BỘ ({len(dates)} KỲ)"]

    for dt in dates:
        actual_result = data_map.get(dt, [])
        past_history = [d for d in sorted_dataset if d["date"] < dt]
        
        # Sinh dàn 80 bộ số từ Ma trận rộng Top 30
        predicted_combos = generate_v5_max_matrix(past_history, game=game, num_combos=80)
        
        # Bóc tách bộ số trùng cao nhất
        best_matched = []
        max_count = 0
        for combo in predicted_combos:
            matched = sorted(list(set(actual_result) & set(combo)))
            if len(matched) > max_count:
                max_count = len(matched)
                best_matched = matched
                
        total_max_match += max_count
        
        # Nhãn đánh dấu kết quả
        if max_count >= 5:
            status = "🔥 [JACKPOT/NỔ LỚN]"
        elif max_count >= 4:
            status = "⚡ [TRÚNG LỚN]"
        elif max_count == 3:
            status = "✅"
        else:
            status = "❌"
            
        lines.append(f"📅 {dt}: Trùng tối đa {max_count}/6 {status} {best_matched}")

    avg_match = total_max_match / len(dates) if dates else 0
    lines.append(f"\n📊 TB Trúng Tối Đa: {avg_match:.1f}/6 số")
    
    bot.send_message(message.chat.id, "\n".join(lines))

if __name__ == "__main__":
    bot.infinity_polling(timeout=60, long_polling_timeout=30)