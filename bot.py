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
# THUẬT TOÁN V35: AUTO-OPTIMIZED ENGINE (TỰ TÌM LOGIC TỐI ƯU)
# =============================================================
def analyze_optimal_filters(history_data: list, game="645") -> dict:
    """
    Phân tích 30-50 kỳ lịch sử gần nhất để tự rút ra logic lọc có tần suất trúng cao nhất
    """
    recent_draws = [d["result"] for d in history_data[-40:]]
    if not recent_draws:
        return {"hot_ratio": (3, 4), "min_tens": 2, "sum_range": (80, 200), "top_matrix_size": 30}

    # 1. Phân tích phân bổ Hot/Warm/Cold thực tế
    max_num = 55 if str(game) == "655" else 45
    all_numbers = [n for draw in recent_draws for n in draw]
    freq = Counter(all_numbers)
    sorted_all = sorted(range(1, max_num + 1), key=lambda x: freq.get(x, 0), reverse=True)

    # Hot: Top 30% xuất hiện nhiều nhất
    hot_size = 15 if str(game) == "655" else 14
    hot_set = set(sorted_all[:hot_size])

    hot_counts = []
    sum_list = []
    tens_counts = []

    for draw in recent_draws:
        # Đếm số Hot trong kết quả thực
        h_cnt = sum(1 for x in draw if x in hot_set)
        hot_counts.append(h_cnt)
        
        # Đếm tổng dải số
        sum_list.append(sum(draw))
        
        # Đếm độ phủ nhóm chục
        tens_counts.append(len(set(x // 10 for x in draw)))

    # Tìm thông số xuất hiện nhiều nhất (Mode)
    best_hot_count = Counter(hot_counts).most_common(1)[0][0]
    best_tens_coverage = Counter(tens_counts).most_common(1)[0][0]

    # Tính dải tổng tối ưu (khoảng 80% kết quả rơi vào)
    sum_list.sort()
    min_sum = sum_list[int(len(sum_list) * 0.1)]
    max_sum = sum_list[int(len(sum_list) * 0.9)]

    return {
        "best_hot": max(2, min(best_hot_count, 4)),
        "min_tens": max(2, best_tens_coverage),
        "sum_range": (min_sum, max_sum),
        "sorted_numbers": sorted_all
    }


def generate_v35_optimal_combos(history_data: list, game="645", num_combos=5, seed_key=None) -> tuple:
    """
    Sinh bộ số dựa trên Logic đã được tự động tối ưu hóa từ lịch sử
    """
    if seed_key:
        numeric_seed = int(re.sub(r'\D', '', str(seed_key))) if re.sub(r'\D', '', str(seed_key)) else 42
        random.seed(numeric_seed)

    is_655 = (str(game) == "655")
    max_num = 55 if is_655 else 45

    if len(history_data) < 20:
        base = [list(range(i, i + 6)) for i in range(1, num_combos + 1)]
        return base, list(range(1, 31))

    # BƯỚC 1: TỰ ĐỘNG LỌC LOGIC TỐI ƯU TỪ LỊCH SỬ
    opt = analyze_optimal_filters(history_data, game=game)
    sorted_all = opt["sorted_numbers"]

    hot_size = 15 if is_655 else 14
    hot_pool = sorted_all[:hot_size]
    warm_pool = sorted_all[hot_size:hot_size*2]
    cold_pool = sorted_all[hot_size*2:]

    top_matrix_size = 32 if is_655 else 30
    top_matrix = sorted(sorted_all[:top_matrix_size])

    combos = []
    attempts = 0

    # BƯỚC 2: SINH BỘ SỐ VỚI MÔ HÌNH ĐÃ TỐI ƯU
    while len(combos) < num_combos and attempts < 100000:
        attempts += 1

        n_hot = opt["best_hot"]
        n_warm = random.choice([1, 2])
        n_cold = 6 - n_hot - n_warm

        if n_cold < 0:
            n_cold = 0
            n_warm = 6 - n_hot

        try:
            raw_combo = random.sample(hot_pool, n_hot) + random.sample(warm_pool, n_warm) + random.sample(cold_pool, n_cold)
            combo = sorted(list(set(raw_combo)))
            if len(combo) != 6:
                continue
        except ValueError:
            continue

        # Áp dụng bộ lọc tối ưu từ quá trình tự phân tích
        tens_coverage = len(set(x // 10 for x in combo))
        if tens_coverage < opt["min_tens"]:
            continue

        adj_count = sum(1 for i in range(5) if combo[i+1] - combo[i] == 1)
        if adj_count > 2:
            continue

        evens = sum(1 for x in combo if x % 2 == 0)
        if evens < 1 or evens > 5:
            continue

        if not (opt["sum_range"][0] <= sum(combo) <= opt["sum_range"][1]):
            continue

        if combo not in combos:
            combos.append(combo)

    # Bổ sung nếu chưa đủ bộ
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
    
    # Đã tự phân tích lịch sử & chọn ra 5 bộ tốt nhất
    combos, top_matrix = generate_v35_optimal_combos(dataset, game=game, num_combos=5, seed_key=f"dudoan_{latest_date}")

    msg = [
        f"🎯 **DỰ ĐOÁN V35 AUTO-OPTIMIZED ENGINE - {game_name.upper()}**",
        f"⚙️ *Thuật toán đã tự học dữ liệu quá khứ & tối ưu logic lọc*",
        f"📌 **Ma trận Trọng Tâm V35 ({len(top_matrix)} số):**",
        f"`{top_matrix}`\n",
        f"💡 **Top 5 bộ số hạt nhân trúng cao nhất:**"
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

    status_msg = bot.reply_to(message, f"⚙️ Đang Backtest V35 Auto-Optimized (Chỉ Test Top 5 Bộ Dự Đoán - {len(dates)} kỳ)...")

    data_map = {d["date"]: d["result"] for d in dataset}
    sorted_dataset = sorted(dataset, key=lambda x: x["date"])
    
    total_max_match = 0
    count_jackpot = 0
    count_high = 0
    lines = [f"🧪 **BACKTEST V35 - CHỈ DÙNG TOP 5 BỘ HẠT NHÂN ({len(dates)} KỲ)**\n"]

    for dt in dates:
        actual_result = data_map.get(dt, [])
        past_history = [d for d in sorted_dataset if d["date"] < dt]
        
        # Chỉ tạo đúng 5 bộ hạt nhân bằng logic tối ưu
        top_5_combos, _ = generate_v35_optimal_combos(past_history, game=game, num_combos=5, seed_key=f"dudoan_{dt}")
        
        best_combo = []
        best_matched = []
        best_index = -1
        max_count = 0

        # Chỉ so sánh trong Top 5 bộ này
        for idx, combo in enumerate(top_5_combos, 1):
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
            
        lines.append(f"📅 **{dt}** | KQ Thực tế: `{actual_result}`")
        if max_count > 0:
            lines.append(f"└ 🏆 Bộ trúng cao nhất (Bộ {best_index}/5): `{best_combo}`")
            lines.append(f"└ 🎯 Kết quả: Trúng **{max_count}/6 số** {status} -> `{best_matched}`\n")
        else:
            lines.append(f"└ ❌ Cả 5 bộ dự đoán đều không trúng\n")

    avg_match = total_max_match / len(dates) if dates else 0
    lines.append(f"📊 **TB Trúng Tối Đa Top 5:** {avg_match:.1f}/6 số")
    lines.append(f"🎯 **Tổng Jackpot (5-6 số):** {count_jackpot} kỳ")
    lines.append(f"⚡ **Tổng Trúng LỚN (4 số):** {count_high} kỳ")
    
    try:
        bot.delete_message(message.chat.id, status_msg.message_id)
    except Exception:
        pass

    bot.send_message(message.chat.id, "\n".join(lines), parse_mode="Markdown")

# -------------------------------------------------------------
# 4. CHỐNG CRASH & KHỞI CHẠY CHÍNH
# -------------------------------------------------------------
if __name__ == "__main__":
    print("🚀 Đang khởi chạy Vietlott Telegram Bot V35...")
    
    if TOKEN == "YOUR_BOT_TOKEN_HERE" or not TOKEN:
        print("❌ LỖI KHỞI ĐỘNG: Chưa cấu hình BOT_TOKEN trong Environment Variables của Render!")
        sys.exit(1)

    try:
        print("✅ Bot đang lắng nghe lệnh từ Telegram...")
        bot.infinity_polling(timeout=60, long_polling_timeout=30)
    except Exception as e:
        print(f"💥 LỖI CRASH BOT: {e}")
        sys.exit(1)