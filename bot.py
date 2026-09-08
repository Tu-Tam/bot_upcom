import os
import re
import threading
from flask import Flask
import telebot
from collections import Counter
import random
import itertools
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

def generate_v21_max_coverage(history_data: list, game="655", num_combos=150) -> tuple:
    """
    Thuật toán V21: Greedy Maximum Coverage & Pure Uniform Quadrant Distribution
    Tối đa hóa khoảng cách giữa các bộ số để tăng diện tích phủ bẫy 5-6 số.
    """
    is_655 = (str(game) == "655")
    max_num = 55 if is_655 else 45

    # 1. Phân ma trận thành 4 Quadrant (Dải số)
    q1 = list(range(1, max_num // 4 + 1))
    q2 = list(range(max_num // 4 + 1, max_num // 2 + 1))
    q3 = list(range(max_num // 2 + 1, (3 * max_num) // 4 + 1))
    q4 = list(range((3 * max_num) // 4 + 1, max_num + 1))

    top_matrix = list(range(1, max_num + 1))

    # 2. Thuật toán Phủ Tham Ăn Cực Đại (Greedy Maximum Coverage)
    combos = []
    attempts = 0
    random.seed(len(history_data) + 2026)

    while len(combos) < num_combos and attempts < 30000:
        attempts += 1

        # Phân bổ quy chuẩn: 1-2 số từ mỗi Dải Quadrant
        c1 = random.sample(q1, random.choice([1, 2]))
        c2 = random.sample(q2, random.choice([1, 2]))
        c3 = random.sample(q3, random.choice([1, 2]))
        
        needed = 6 - len(c1) - len(c2) - len(c3)
        if needed <= 0 or needed > len(q4):
            continue

        c4 = random.sample(q4, needed)
        combo = sorted(c1 + c2 + c3 + c4)

        # Điều kiện 1: Tỷ lệ Chẵn/Lẻ chuẩn (2-4, 3-3, 4-2)
        evens = sum(1 for x in combo if x % 2 == 0)
        if evens < 2 or evens > 4:
            continue

        # Điều kiện 2: Khống chế Tổng dãy số
        total_sum = sum(combo)
        min_s = 90 if is_655 else 70
        max_s = 230 if is_655 else 185
        if not (min_s <= total_sum <= max_s):
            continue

        # Điều kiện 3: Ép khoảng cách tối đa (Chỉ cho phép trùng tối đa 3 số với các bộ đã chọn)
        if combos and attempts < 22000:
            max_overlap = max(len(set(combo) & set(c)) for c in combos)
            if max_overlap > 3:  # Ép không gian phủ rải rộng tuyệt đối
                continue

        if combo not in combos:
            combos.append(combo)

    # Nới lỏng nhẹ nếu chưa đủ 150 bộ
    while len(combos) < num_combos:
        combo = sorted(random.sample(top_matrix, 6))
        if combo not in combos:
            combos.append(combo)

    return combos, top_matrix[:28]

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

# -------------------------------------------------------------
# 3. TELEGRAM COMMAND HANDLERS
# -------------------------------------------------------------

@bot.message_handler(commands=['reload'])
def handle_reload(message):
    bot.reply_to(message, "⏳ Đang cào dữ liệu mới từ Vietlott...")
    data_655 = fetch_vietlott_655_data(300)
    data_645 = fetch_vietlott_645_data(300)
    bot.send_message(message.chat.id, f"🔄 Đã cập nhật CSDL:\n- Power 6/55: {len(data_655)} kỳ\n- Mega 6/45: {len(data_645)} kỳ")

@bot.message_handler(commands=['dudoan655', 'dudoan645'])
def handle_dudoan(message):
    cmd = message.text.split()[0].lower()
    game = "645" if "645" in cmd else "655"
    game_name = "Power 6/55" if game == "655" else "Mega 6/45"

    dataset = get_dataset(game)
    if not dataset:
        bot.reply_to(message, f"❌ Chưa có dữ liệu {game_name}. Hãy gõ /reload trước!")
        return

    combos, top_matrix = generate_v21_max_coverage(dataset, game=game, num_combos=5)

    msg = [
        f"🎯 **DỰ ĐOÁN KỲ TỚI V21 MAX COVERAGE - {game_name.upper()}**",
        f"📌 **Ma trận Bao Phủ Tuyệt Đối ({len(top_matrix)} số):**",
        f"`{top_matrix}`\n",
        f"💡 **Dàn 5 bộ số hạt nhân đi kèm:**"
    ]
    for i, cb in enumerate(combos, 1):
        msg.append(f"Bộ {i}: `{cb}`")

    bot.send_message(message.chat.id, "\n".join(msg), parse_mode="Markdown")

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
    lines = [f"🧪 BACKTEST MAX COVERAGE V21 {game} - DÀN 150 BỘ ({len(dates)} KỲ)"]

    for dt in dates:
        actual_result = data_map.get(dt, [])
        past_history = [d for d in sorted_dataset if d["date"] < dt]
        
        predicted_combos, _ = generate_v21_max_coverage(past_history, game=game, num_combos=150)
        
        best_matched = []
        max_count = 0
        for combo in predicted_combos:
            matched = sorted(list(set(actual_result) & set(combo)))
            if len(matched) > max_count:
                max_count = len(matched)
                best_matched = matched
                
        total_max_match += max_count
        
        if max_count >= 5:
            status = "🔥 [JACKPOT / NỔ 5-6 SỐ]"
        elif max_count == 4:
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