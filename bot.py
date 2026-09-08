import os
import re
import threading
from flask import Flask
import telebot
from collections import Counter
from vietlott_scraper import fetch_vietlott_655_data, fetch_vietlott_645_data, get_dataset

# -------------------------------------------------------------
# 1. WEB SERVER CHỐNG SẬP TỰ ĐỘNG TRÊN RENDER
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
# 2. KHỞI TẠO BOT TELEGRAM
# -------------------------------------------------------------
TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
bot = telebot.TeleBot(TOKEN)

def generate_hybrid_prediction(history_data: list, game="655") -> list:
    """
    Thuật toán Hybrid: Chỉ dùng dữ liệu CÁC KỲ TRƯỚC thời điểm test 
    để tính toán tần suất + độ gan, tạo ra bộ số dự đoán tối ưu.
    """
    if len(history_data) < 10:
        return [1, 2, 3, 4, 5, 6]

    max_num = 55 if str(game) == "655" else 45
    recent_draws = [d["result"] for d in history_data[-40:]] # Lấy 40 kỳ liền trước

    # Tần suất
    flat_nums = [n for draw in recent_draws for n in draw]
    freq = Counter(flat_nums)

    # Độ gan (số kỳ chưa về)
    last_seen = {}
    for idx, draw in enumerate(reversed(recent_draws)):
        for n in draw:
            if n not in last_seen:
                last_seen[n] = idx

    # Tính điểm ưu tiên
    scores = {}
    for n in range(1, max_num + 1):
        f_score = freq.get(n, 0) / len(recent_draws)
        r_score = last_seen.get(n, 40)
        scores[n] = (f_score * 0.6) + ((1 / (r_score + 1)) * 0.4)

    # Top 6 số có điểm cao nhất
    top_6 = sorted(scores, key=scores.get, reverse=True)[:6]
    return sorted(top_6)

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
    
    total_match = 0
    lines = [f"🧪 BACKTEST HYBRID {game} ({len(dates)} KỲ)"]

    for dt in dates:
        actual_result = data_map.get(dt, [])
        
        # Lấy lịch sử CÁC KỲ QUAY TRƯỚC ngày đang test để làm dữ liệu dự đoán
        past_history = [d for d in sorted_dataset if d["date"] < dt]
        
        # Tạo bộ số dự đoán động dựa trên thuật toán
        predicted = generate_hybrid_prediction(past_history, game=game)
        
        matched = sorted(list(set(actual_result) & set(predicted)))
        count = len(matched)
        total_match += count
        
        status = "✅" if count >= 3 else "❌"
        lines.append(f"📅 {dt}: Trùng {count}/6 {status} {matched}")

    avg_match = total_match / len(dates) if dates else 0
    lines.append(f"\n📊 TB: {avg_match:.1f}/6 số")
    
    bot.send_message(message.chat.id, "\n".join(lines))

if __name__ == "__main__":
    bot.infinity_polling(timeout=60, long_polling_timeout=30)