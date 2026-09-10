import os
import re
import sys
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

# =============================================================
# THUẬT TOÁN V34.1: ENTROPY SWARM (CÓ SEED CỐ ĐỊNH & TUNING 6/55)
# =============================================================
def generate_v34_entropy_swarm(history_data: list, game="655", num_combos=150, seed_key=None) -> tuple:
    """
    Thuật toán V34.1 với Seed cố định & Tinh chỉnh dải số cho 6/55 và 6/45
    """
    if seed_key:
        numeric_seed = int(re.sub(r'\D', '', str(seed_key))) if re.sub(r'\D', '', str(seed_key)) else 42
        random.seed(numeric_seed)

    is_655 = (str(game) == "655")
    max_num = 55 if is_655 else 45
    
    if len(history_data) < 20:
        base = list(range(1, 7))
        return [base] * num_combos, base

    draws_recent = [d["result"] for d in history_data[-60:]]
    freq = Counter([n for draw in draws_recent for n in draw])
    
    sorted_all = sorted(range(1, max_num + 1), key=lambda x: freq.get(x, 0), reverse=True)

    # Tinh chỉnh V34.1: Co hẹp ma trận cho Power 6/55
    if is_655:
        hot_pool = sorted_all[:15]
        warm_pool = sorted_all[15:30]
        cold_pool = sorted_all[30:]
        top_matrix = sorted(sorted_all[:32])
        min_tens = 2
    else:
        hot_pool = sorted_all[:14]
        warm_pool = sorted_all[14:28]
        cold_pool = sorted_all[28:]
        top_matrix = sorted(sorted_all[:30])
        min_tens = 3

    min_s, max_s = (85, 230) if is_655 else (60, 200)
    
    combos = []
    attempts = 0

    while len(combos) < num_combos and attempts < 100000:
        attempts += 1

        n_hot = random.choice([3, 4])
        n_warm = random.choice([1, 2])
        n_cold = 6 - n_hot - n_warm

        if n_cold <= 0:
            n_cold = 1

        try:
            raw_combo = random.sample(hot_pool, n_hot) + random.sample(warm_pool, n_warm) + random.sample(cold_pool, n_cold)
            # Ép chuẩn đúng 6 số
            combo = sorted(list(set(raw_combo)))
            if len(combo) != 6:
                continue
        except ValueError:
            continue

        # Lọc 1: Kiểm tra khoảng cách các chục
        tens_coverage = len(set(x // 10 for x in combo))
        if tens_coverage < min_tens:
            continue

        # Lọc 2: Tối đa 2 cặp liền kề
        adj_count = sum(1 for i in range(5) if combo[i+1] - combo[i] == 1)
        if adj_count > 2:
            continue

        # Lọc 3: Tỷ lệ Chẵn / Lẻ (1-5 đến 5-1)
        evens = sum(1 for x in combo if x % 2 == 0)
        if evens < 1 or evens > 5:
            continue

        # Lọc 4: Tổng dải rộng
        if not (min_s <= sum(combo) <= max_s):
            continue

        # Lọc 5: Giảm trùng lặp nội bộ
        if combos and attempts < 70000:
            limit = 4 if len(combos) < 100 else 5
            if max(len(set(combo) & set(c)) for c in combos) > limit:
                continue

        if combo not in combos:
            combos.append(combo)

    # Nới lỏng bổ sung từ Ma trận trọng tâm nếu chưa đủ 150 bộ
    while len(combos) < num_combos:
        combo = sorted(random.sample(top_matrix, 6))
        if combo not in combos:
            combos.append(combo)

    return combos, top_matrix

def parse_date_range(raw_text: str, dataset: list) -> list:
    clean_text = re.sub(r'/(test655|test645|test)', '', raw_text).strip()
    clean_text = re.sub(r'^(655|645)', '', clean_text).strip()
    
    sorted_dataset = sorted(dataset, key=lambda x: x["date"])
    
    match = re.search(r'(\d{4}-\d{2}-\d{2})\s*(?:=>|->|-|\s+)\s*(\d{1,3}|\d{4}-\d{2}-\d{2})$', clean_text)
    
    if match:
        start_str, end_val = match.group(1), match.group(2)
        future_draws = [d["date"] for d in sorted_dataset if d["date"] >= start_str]
        
        if end_val.isdigit():
            return future_draws[:int(end_val)]
        else:
            return [dt for dt in future_draws if dt <= end_val]

    single_date = re.search(r'(\d{4}-\d{2}-\d{2})', clean_text)
    if single_date:
        dt_str = single_date.group(1)
        return [d["date"] for d in sorted_dataset if d["date"] == dt_str]

    return []

# -------------------------------------------------------------
# 3. TELEGRAM COMMAND HANDLERS
# -------------------------------------------------------------

@bot.message_handler(commands=['reload'])
def handle_reload(message):
    bot.reply_to(message, "⏳ Đang cào dữ liệu mới từ Vietlott...")
    
    def async_fetch():
        try:
            data_655 = fetch_vietlott_655_data(300)
            data_645 = fetch_vietlott_645_data(300)
            bot.send_message(
                message.chat.id, 
                f"🔄 Đã cập nhật xong CSDL:\n- Power 6/55: {len(data_655)} kỳ\n- Mega 6/45: {len(data_645)} kỳ"
            )
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Lỗi cào dữ liệu: {e}")

    threading.Thread(target=async_fetch).start()

@bot.message_handler(commands=['dudoan655', 'dudoan645'])
def handle_dudoan(message):
    cmd = message.text.split()[0].lower()
    game = "645" if "645" in cmd else "655"
    game_name = "Power 6/55" if game == "655" else "Mega 6/45"

    dataset = get_dataset(game)
    if not dataset:
        bot.reply_to(message, f"⏳ CSDL {game_name} đang trống. Đang cào dữ liệu, vui lòng thử lại sau 15 giây!")
        threading.Thread(target=fetch_vietlott_645_data if game == "645" else fetch_vietlott_655_data, args=(300,)).start()
        return

    latest_date = max(d["date"] for d in dataset) if dataset else "2026-01-01"
    combos, top_matrix = generate_v34_entropy_swarm(dataset, game=game, num_combos=5, seed_key=f"dudoan_{latest_date}")

    msg = [
        f"🎯 **DỰ ĐOÁN KỲ TỚI V34.1 ENTROPY SWARM - {game_name.upper()}**",
        f"📌 **Ma trận Trọng Tâm V34.1 ({len(top_matrix)} số):**",
        f"`{top_matrix}`\n",
        f"💡 **Dàn 5 bộ số hạt nhân săn Jackpot:**"
    ]
    for i, cb in enumerate(combos, 1):
        msg.append(f"Bộ {i}: `{cb}`")

    bot.send_message(message.chat.id, "\n".join(msg), parse_mode="Markdown")

@bot.message_handler(commands=['test', 'test645', 'test655'])
def handle_test(message):
    raw_args = message.text.strip()
    game = "645" if "645" in raw_args else "655"
    game_name = "Mega 6/45" if game == "645" else "Power 6/55"
    
    dataset = get_dataset(game)
    
    if not dataset:
        bot.reply_to(message, f"⏳ CSDL {game_name} chưa sẵn sàng. Đang cào dữ liệu, vui lòng thử lại sau 15 giây!")
        threading.Thread(target=fetch_vietlott_645_data if game == "645" else fetch_vietlott_655_data, args=(300,)).start()
        return

    dates = parse_date_range(raw_args, dataset)
    
    if not dates:
        bot.reply_to(message, f"❌ Cú pháp chưa đúng hoặc không tìm thấy ngày trong CSDL!\n👉 Thử lại: `/test {game} 2026-09-01 => 30`", parse_mode="Markdown")
        return

    status_msg = bot.reply_to(message, f"⚙️ Đang chạy Backtest V34.1 {game_name} ({len(dates)} kỳ)...")

    data_map = {d["date"]: d["result"] for d in dataset}
    sorted_dataset = sorted(dataset, key=lambda x: x["date"])
    
    total_max_match = 0
    count_jackpot = 0
    count_high = 0
    lines = [f"🧪 **BACKTEST V34.1 {game} - DÀN 150 BỘ ({len(dates)} KỲ)**\n"]

    for dt in dates:
        actual_result = data_map.get(dt, [])
        past_history = [d for d in sorted_dataset if d["date"] < dt]
        
        # Khóa seed theo từng ngày để kết quả kiểm tra nhất quán
        predicted_combos, _ = generate_v34_entropy_swarm(past_history, game=game, num_combos=150, seed_key=dt)
        
        best_combo = []
        best_matched = []
        best_index = -1
        max_count = 0

        # Tìm bộ số trúng cao nhất trong dàn 150 bộ
        for idx, combo in enumerate(predicted_combos, 1):
            matched = sorted(list(set(actual_result) & set(combo)))
            if len(matched) > max_count:
                max_count = len(matched)
                best_matched = matched
                best_combo = combo
                best_index = idx
                
        total_max_match += max_count
        
        if max_count >= 5:
            status = "🔥 [JACKPOT / NỔ 5-6 SỐ]"
            count_jackpot += 1
        elif max_count == 4:
            status = "⚡ [TRÚNG LỚN 4 SỐ]"
            count_high += 1
        elif max_count == 3:
            status = "✅ [TRÚNG 3 SỐ]"
        else:
            status = "❌ [XỊT]"
            
        # In chi tiết bộ số tốt nhất và các số trùng
        lines.append(f"📅 **{dt}** | KQ Thực tế: `{actual_result}`")
        lines.append(f"└ 🏆 Bộ số trúng cao nhất (Bộ {best_index}): `{best_combo}`")
        lines.append(f"└ 🎯 Kết quả: Trúng **{max_count}/6 số** {status} -> `{best_matched}`\n")

    avg_match = total_max_match / len(dates) if dates else 0
    lines.append(f"📊 **TB Trúng Tối Đa:** {avg_match:.1f}/6 số")
    lines.append(f"🎯 **Tổng Jackpot (5-6 số):** {count_jackpot} kỳ")
    lines.append(f"⚡ **Tổng Trúng Lớn (4 số):** {count_high} kỳ")
    
    try:
        bot.delete_message(message.chat.id, status_msg.message_id)
    except Exception:
        pass

    bot.send_message(message.chat.id, "\n".join(lines), parse_mode="Markdown")

# -------------------------------------------------------------
# 4. CHỐNG CRASH & KHỞI CHẠY CHÍNH
# -------------------------------------------------------------
if __name__ == "__main__":
    print("🚀 Đang khởi chạy Vietlott Telegram Bot...")
    
    if TOKEN == "YOUR_BOT_TOKEN_HERE" or not TOKEN:
        print("❌ LỖI KHỞI ĐỘNG: Chưa cấu hình BOT_TOKEN trong Environment Variables của Render!")
        sys.exit(1)

    try:
        print("✅ Bot đang lắng nghe lệnh từ Telegram...")
        bot.infinity_polling(timeout=60, long_polling_timeout=30)
    except Exception as e:
        print(f"💥 LỖI CRASH BOT: {e}")
        sys.exit(1)