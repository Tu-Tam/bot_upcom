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

def generate_v8_genetic_matrix(history_data: list, game="655", num_combos=100) -> tuple:
    """
    Thuật toán V8: Ma trận Tối ưu Di truyền & Phủ đa dạng điểm (Diversity Covering)
    Giúp đẩy tối đa cơ hội bắt trúng 5-6 số.
    """
    if len(history_data) < 10:
        return [[1, 2, 3, 4, 5, 6]], [1, 2, 3, 4, 5, 6]

    is_655 = (str(game) == "655")
    max_num = 55 if is_655 else 45
    top_n_matrix = 22 if is_655 else 18  # Ma trận Bao 18/22

    recent_draws = [d["result"] for d in history_data[-80:]]

    # 1. Thống kê Tần suất & Chu kỳ gan
    flat_nums = [n for draw in recent_draws for n in draw]
    freq = Counter(flat_nums)

    last_seen = {}
    for idx, draw in enumerate(reversed(recent_draws)):
        for n in draw:
            if n not in last_seen:
                last_seen[n] = idx

    # 2. Chấm điểm Trọng số Đa tầng
    scores = {}
    for n in range(1, max_num + 1):
        f_score = freq.get(n, 0) / len(recent_draws)
        r_score = last_seen.get(n, 80)
        
        # Tần suất (40%) + Chu kỳ nhịp rơi (40%) + Điểm đột biến (20%)
        scores[n] = (f_score * 0.4) + ((1 / (r_score + 1)) * 0.4) + (random.uniform(0.01, 0.08))

    # Lấy Top candidates làm Ma trận gốc
    top_candidates = sorted(scores, key=scores.get, reverse=True)[:top_n_matrix]

    # 3. Sinh Quần thể Ban đầu (Population Sampling)
    population = []
    attempts = 0
    random.seed(len(history_data))

    while len(population) < 800 and attempts < 4000:
        attempts += 1
        combo = sorted(random.sample(top_candidates, 6))

        # Điều kiện 1: Tỷ lệ Chẵn / Lẻ
        evens = sum(1 for x in combo if x % 2 == 0)
        if evens < 2 or evens > 4:
            continue

        # Điều kiện 2: Tổng dãy số
        total_sum = sum(combo)
        min_s = 85 if is_655 else 70
        max_s = 230 if is_655 else 190
        if not (min_s <= total_sum <= max_s):
            continue

        # Điều kiện 3: Khoảng cách giữa các số (Lọc dãy số liền nhau quá 3 số)
        has_3_consecutive = any(combo[i+2] - combo[i] == 2 for i in range(len(combo)-2))
        if has_3_consecutive:
            continue

        if combo not in population:
            population.append(combo)

    # 4. Sàng lọc Di truyền chọn N bộ có độ bao phủ tối đa (Maximal Diversity)
    selected_combos = []
    if population:
        selected_combos.append(population[0])
        
        for candidate in population[1:]:
            if len(selected_combos) >= num_combos:
                break
            
            # Kiểm tra độ trùng lặp với các bộ đã chọn (chỉ lấy bộ trùng tối đa 3-4 số)
            max_overlap = max(len(set(candidate) & set(sc)) for sc in selected_combos)
            if max_overlap <= 4:
                selected_combos.append(candidate)

        # Nếu chưa đủ bộ thì nạp nốt từ quần thể
        while len(selected_combos) < num_combos and len(selected_combos) < len(population):
            for p in population:
                if p not in selected_combos:
                    selected_combos.append(p)
                    if len(selected_combos) >= num_combos:
                        break

    return selected_combos if selected_combos else [top_candidates[:6]], sorted(top_candidates)

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

    combos, top_matrix = generate_v8_genetic_matrix(dataset, game=game, num_combos=5)

    msg = [
        f"🎯 **DỰ ĐOÁN KỲ TỚI V8 GENETIC - {game_name.upper()}**",
        f"📌 **Ma trận Bao tối ưu ({len(top_matrix)} số):**",
        f"`{top_matrix}`\n",
        f"💡 **Dàn 5 bộ số phân bố tối ưu:**"
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
    lines = [f"🧪 BACKTEST GENETIC V8 {game} - DÀN 100 BỘ ({len(dates)} KỲ)"]

    for dt in dates:
        actual_result = data_map.get(dt, [])
        past_history = [d for d in sorted_dataset if d["date"] < dt]
        
        # Sinh dàn 100 bộ theo cơ chế Thuật toán Di truyền & Phủ tối đa
        predicted_combos, _ = generate_v8_genetic_matrix(past_history, game=game, num_combos=100)
        
        best_matched = []
        max_count = 0
        for combo in predicted_combos:
            matched = sorted(list(set(actual_result) & set(combo)))
            if len(matched) > max_count:
                max_count = len(matched)
                best_matched = matched
                
        total_max_match += max_count
        
        if max_count >= 5:
            status = "🔥 [NỔ 5-6 SỐ / JACKPOT]"
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