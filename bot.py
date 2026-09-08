import os
import re
import threading
from flask import Flask
import telebot
from collections import Counter, defaultdict
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

def generate_v27_dynamic_pivot(history_data: list, game="655", num_combos=150) -> tuple:
    """
    Thuật toán V27: Multi-Pivot Dynamic Covering & Set-Cover Optimization
    Phát triển bộ số từ cặp điểm tựa linh hoạt và phủ tối đa tập 3 số.
    """
    is_655 = (str(game) == "655")
    max_num = 55 if is_655 else 45
    
    if len(history_data) < 20:
        base = list(range(1, 7))
        return [base], base

    draws_recent = [d["result"] for d in history_data[-50:]]
    freq = Counter([n for draw in draws_recent for n in draw])
    
    pair_weights = defaultdict(int)
    for draw in draws_recent:
        for p1, p2 in itertools.combinations(sorted(draw), 2):
            pair_weights[(p1, p2)] += 1

    sorted_all = sorted(range(1, max_num + 1), key=lambda x: freq.get(x, 0), reverse=True)
    
    hot_pool = sorted_all[:18]
    warm_pool = sorted_all[18:32]
    top_matrix = sorted(hot_pool + warm_pool[:12])

    # Tạo danh sách các cặp Pivot có trọng số tương quan cao nhất
    pivot_pairs = []
    for p1, p2 in itertools.combinations(hot_pool, 2):
        weight = pair_weights.get(tuple(sorted([p1, p2])), 0)
        pivot_pairs.append((p1, p2, weight))
    pivot_pairs.sort(key=lambda x: x[2], reverse=True)
    top_pivots = [(p[0], p[1]) for p in pivot_pairs[:25]]

    combos = []
    attempts = 0
    random.seed(len(history_data) + 2026)

    min_s = 95 if is_655 else 75
    max_s = 215 if is_655 else 185

    while len(combos) < num_combos and attempts < 60000:
        attempts += 1

        # 1. Chọn ngẫu nhiên 1 Cặp Điểm Tựa (Pivot Pair) từ Top 25
        p1, p2 = random.choice(top_pivots)

        # 2. Chọn 3 số từ Top Matrix có độ tương quan cao với cặp Pivot
        candidates = [n for n in top_matrix if n not in (p1, p2)]
        candidates.sort(key=lambda x: pair_weights.get(tuple(sorted([p1, x])), 0) + 
                                     pair_weights.get(tuple(sorted([p2, x])), 0), reverse=True)
        
        selected_3 = random.sample(candidates[:12], 3)

        # 3. Chọn 1 số Bắt Lạnh từ ngoài Hot/Warm Pool
        cold_candidate = random.choice([n for n in sorted_all[30:] if n not in selected_3])

        combo = sorted([p1, p2] + selected_3 + [cold_candidate])

        # Lọc 1: Không quá 1 cặp liền kề
        adj_count = sum(1 for i in range(5) if combo[i+1] - combo[i] == 1)
        if adj_count > 1:
            continue

        # Lọc 2: Tỷ lệ Chẵn/Lẻ (2-4, 3-3, 4-2)
        evens = sum(1 for x in combo if x % 2 == 0)
        if evens < 2 or evens > 4:
            continue

        # Lọc 3: Tổng Chuẩn Gaussian
        if not (min_s <= sum(combo) <= max_s):
            continue

        # Lọc 4: Khoảng cách giữa các số (Max Gap <= 22)
        gaps = [combo[i+1] - combo[i] for i in range(5)]
        if max(gaps) > 22:
            continue

        # Lọc 5: Optimal Hamming Distance Limit (ép <= 3 cho 120 bộ đầu)
        if combos and attempts < 45000:
            limit = 3 if len(combos) < 120 else 4
            if max(len(set(combo) & set(c)) for c in combos) > limit:
                continue

        if combo not in combos:
            combos.append(combo)

    # Bổ sung bộ số nếu chưa đủ 150
    while len(combos) < num_combos:
        combo = sorted(random.sample(top_matrix, 6))
        if combo not in combos:
            combos.append(combo)

    return combos, top_matrix

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

    combos, top_matrix = generate_v27_dynamic_pivot(dataset, game=game, num_combos=5)

    msg = [
        f"🎯 **DỰ ĐOÁN KỲ TỚI V27 DYNAMIC PIVOT - {game_name.upper()}**",
        f"📌 **Ma trận Tương Quan Phủ Điểm Tựa ({len(top_matrix)} số):**",
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
    lines = [f"🧪 BACKTEST DYNAMIC PIVOT V27 {game} - DÀN 150 BỘ ({len(dates)} KỲ)"]

    for dt in dates:
        actual_result = data_map.get(dt, [])
        past_history = [d for d in sorted_dataset if d["date"] < dt]
        
        predicted_combos, _ = generate_v27_dynamic_pivot(past_history, game=game, num_combos=150)
        
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