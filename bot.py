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

def generate_v31_jackpot_hunter(history_data: list, game="655", num_combos=150) -> tuple:
    """
    Thuật toán V31: Dynamic High-Cluster Jackpot Hunter
    Tập trung tối đa xác suất trúng 5-6 số bằng Ma trận Điểm nóng thu hẹp (24-26 số)
    và Ma trận liên kết Cặp (Co-occurrence Pair Clusters).
    """
    is_655 = (str(game) == "655")
    max_num = 55 if is_655 else 45
    
    if len(history_data) < 20:
        base = list(range(1, 7))
        return [base], base

    draws_recent = [d["result"] for d in history_data[-50:]]
    freq = Counter([n for draw in draws_recent for n in draw])
    sorted_all = sorted(range(1, max_num + 1), key=lambda x: freq.get(x, 0), reverse=True)

    # Tính toán Ma trận Cặp số thường xuyên đi cùng nhau
    pair_freq = defaultdict(int)
    for draw in draws_recent:
        for p1, p2 in itertools.combinations(sorted(draw), 2):
            pair_freq[(p1, p2)] += 1

    combos = []
    attempts = 0

    # Thu hẹp Ma trận trọng tâm để dồn mật độ trùng 5-6 số
    matrix_size = 26 if is_655 else 22
    top_matrix = sorted(sorted_all[:matrix_size])
    
    # Thiết lập khoảng tổng Gaussian linh hoạt
    min_s, max_s = (100, 210) if is_655 else (70, 190)

    # Tìm danh sách các cặp Hot Pivots có tần suất đi cùng nhau cao nhất
    hot_pairs = sorted(pair_freq.keys(), key=lambda x: pair_freq[x], reverse=True)[:30]

    while len(combos) < num_combos and attempts < 80000:
        attempts += 1

        # 60% Dàn bộ số được dựng từ Cặp Điểm Nóng (Hot Pair Anchors)
        if random.random() < 0.60 and hot_pairs:
            p1, p2 = random.choice(hot_pairs)
            if p1 in top_matrix and p2 in top_matrix:
                rem_candidates = [n for n in top_matrix if n not in (p1, p2)]
                selected = random.sample(rem_candidates, 4)
                combo = sorted([p1, p2] + selected)
            else:
                combo = sorted(random.sample(top_matrix, 6))
        else:
            combo = sorted(random.sample(top_matrix, 6))

        # Lọc 1: Cho phép tối đa 2 cặp liền kề (Tăng cơ hội nổ Jackpot)
        adj_count = sum(1 for i in range(5) if combo[i+1] - combo[i] == 1)
        if adj_count > 2:
            continue

        # Lọc 2: Tỷ lệ Chẵn / Lẻ mở rộng
        evens = sum(1 for x in combo if x % 2 == 0)
        if evens < 1 or evens > 5:
            continue

        # Lọc 3: Kiểm tra Tổng Gaussian
        if not (min_s <= sum(combo) <= max_s):
            continue

        # Lọc 4: Giảm khoảng cách tối đa giữa các bộ số để phủ kín Ma trận
        if combos and attempts < 50000:
            limit = 4 if len(combos) < 100 else 5
            if max(len(set(combo) & set(c)) for c in combos) > limit:
                continue

        if combo not in combos:
            combos.append(combo)

    # Nới lỏng bổ sung nếu chưa đủ bộ
    while len(combos) < num_combos:
        combo = sorted(random.sample(top_matrix, 6))
        if combo not in combos:
            combos.append(combo)

    return combos, top_matrix

def parse_date_range(raw_text: str, dataset: list) -> list:
    """
    Xử lý bóc tách cú pháp tham số ngày từ lệnh /test
    """
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
        data_655 = fetch_vietlott_655_data(300)
        data_645 = fetch_vietlott_645_data(300)
        bot.send_message(
            message.chat.id, 
            f"🔄 Đã cập nhật xong CSDL:\n- Power 6/55: {len(data_655)} kỳ\n- Mega 6/45: {len(data_645)} kỳ"
        )

    threading.Thread(target=async_fetch).start()

@bot.message_handler(commands=['dudoan655', 'dudoan645'])
def handle_dudoan(message):
    cmd = message.text.split()[0].lower()
    game = "645" if "645" in cmd else "655"
    game_name = "Power 6/55" if game == "655" else "Mega 6/45"

    dataset = get_dataset(game)
    if not dataset:
        bot.reply_to(message, f"⏳ CSDL {game_name} đang trống. Đang tự động cào dữ liệu, vui lòng thử lại sau 15 giây!")
        threading.Thread(target=fetch_vietlott_645_data if game == "645" else fetch_vietlott_655_data, args=(300,)).start()
        return

    combos, top_matrix = generate_v31_jackpot_hunter(dataset, game=game, num_combos=5)

    msg = [
        f"🎯 **DỰ ĐOÁN KỲ TỚI V31 JACKPOT HUNTER - {game_name.upper()}**",
        f"📌 **Ma trận Điểm Nóng Săn Jackpot ({len(top_matrix)} số):**",
        f"`{top_matrix}`\n",
        f"💡 **Dàn 5 bộ số hạt nhân cao cấp:**"
    ]
    for i, cb in enumerate(combos, 1):
        msg.append(f"Bộ {i}: `{cb}`")

    bot.send_message(message.chat.id, "\n".join(msg), parse_mode="Markdown")

@bot.message_handler(commands=['test'])
def handle_test(message):
    raw_args = message.text.strip()
    game = "645" if "645" in raw_args else "655"
    game_name = "Mega 6/45" if game == "645" else "Power 6/55"
    
    dataset = get_dataset(game)
    
    if not dataset:
        bot.reply_to(message, f"⏳ CSDL {game_name} chưa sẵn sàng. Đang cào dữ liệu chạy ngầm, vui lòng gõ lại lệnh sau 15 giây!")
        threading.Thread(target=fetch_vietlott_645_data if game == "645" else fetch_vietlott_655_data, args=(300,)).start()
        return

    dates = parse_date_range(raw_args, dataset)
    
    if not dates:
        bot.reply_to(message, f"❌ Cú pháp chưa đúng hoặc không tìm thấy ngày trong CSDL!\n👉 Thử lại: `/test {game} 2026-08-01 => 30`", parse_mode="Markdown")
        return

    # Thông báo cho người dùng biết bot đang tiến hành tính toán
    status_msg = bot.reply_to(message, f"⚙️ Đang chạy Backtest V31 Săn Jackpot {game_name} cho {len(dates)} kỳ...")

    data_map = {d["date"]: d["result"] for d in dataset}
    sorted_dataset = sorted(dataset, key=lambda x: x["date"])
    
    total_max_match = 0
    count_jackpot = 0
    count_high = 0
    lines = [f"🧪 BACKTEST V31 JACKPOT HUNTER {game} - DÀN 150 BỘ ({len(dates)} KỲ)"]

    for dt in dates:
        actual_result = data_map.get(dt, [])
        past_history = [d for d in sorted_dataset if d["date"] < dt]
        
        predicted_combos, _ = generate_v31_jackpot_hunter(past_history, game=game, num_combos=150)
        
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
            count_jackpot += 1
        elif max_count == 4:
            status = "⚡ [TRÚNG LỚN 4 SỐ]"
            count_high += 1
        elif max_count == 3:
            status = "✅"
        else:
            status = "❌"
            
        lines.append(f"📅 {dt}: Trùng tối đa {max_count}/6 {status} {best_matched}")

    avg_match = total_max_match / len(dates) if dates else 0
    lines.append(f"\n📊 TB Trúng Tối Đa: {avg_match:.1f}/6 số")
    lines.append(f"🎯 Tổng nổ 🔥 Jackpot (5-6 số): {count_jackpot} kỳ")
    lines.append(f"⚡ Tổng nổ Trúng Lớn (4 số): {count_high} kỳ")
    
    # Xóa tin nhắn chờ và gửi kết quả hoàn chỉnh
    try:
        bot.delete_message(message.chat.id, status_msg.message_id)
    except Exception:
        pass

    bot.send_message(message.chat.id, "\n".join(lines))

if __name__ == "__main__":
    bot.infinity_polling(timeout=60, long_polling_timeout=30)