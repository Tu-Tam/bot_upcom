import os
import sys
import time
import threading
import json
import re
import random
from collections import Counter
from datetime import datetime, timedelta, date
import telebot
from flask import Flask

# --- CẤU HÌNH TOKEN & WEB SERVER ---
TOKEN = os.getenv("TELEGRAM_TOKEN")

if not TOKEN:
    print("❌ LỖI FATAL: Chưa cấu hình TELEGRAM_TOKEN trong Environment Variables!", flush=True)
    # Tùy chọn: Nhập token trực tiếp nếu chạy local test
    # TOKEN = "YOUR_BOT_TOKEN_HERE"
    sys.exit(1)

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

@app.route('/')
def home():
    return "Vietlott Telegram Bot đang hoạt động!", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# --- CẤU HÌNH DỮ LIỆU CÁC GIẢI VIETLOTT ---
GAME_CONFIG = {
    "655": {"name": "Power 6/55", "max_num": 55, "pick": 6, "type": "standard"},
    "645": {"name": "Mega 6/45", "max_num": 45, "pick": 6, "type": "standard"},
    "3d": {"name": "Max 3D", "length": 3, "type": "digit"},
    "keno": {"name": "Keno", "max_num": 80, "pick": 20, "type": "standard"},
}

# --- GIẢ LẬP CƠ SỞ DỮ LIỆU LỊCH SỬ VIETLOTT ---
# (Trong thực tế, bạn sẽ thay thế danh sách này bằng dữ liệu cào từ CSDL/API)
DATASET = [
    # Power 6/55
    {"date": "2026-08-25", "game": "655", "result": [4, 12, 18, 27, 39, 48]},
    {"date": "2026-08-27", "game": "655", "result": [2, 12, 21, 35, 42, 51]},
    {"date": "2026-08-29", "game": "655", "result": [8, 15, 18, 29, 33, 45]},
    {"date": "2026-09-01", "game": "655", "result": [2, 12, 18, 28, 40, 52]},
    # Mega 6/45
    {"date": "2026-08-26", "game": "645", "result": [5, 11, 23, 31, 38, 41]},
    {"date": "2026-08-28", "game": "645", "result": [1, 11, 19, 23, 34, 40]},
    {"date": "2026-08-30", "game": "645", "result": [5, 14, 23, 30, 39, 44]},
    # Max 3D (3 chữ số)
    {"date": "2026-08-31", "game": "3d", "result": [3, 8, 5]},
    {"date": "2026-09-01", "game": "3d", "result": [7, 2, 9]},
    # Keno (20 số)
    {"date": "2026-09-01", "game": "keno", "result": [3, 7, 12, 15, 18, 22, 25, 31, 34, 39, 41, 45, 50, 53, 58, 62, 67, 71, 75, 79]},
]

# --- THUẬT TOÁN DỰ ĐOÁN & BACKTEST ---
def predict_numbers(game_type: str, history_data: list) -> list:
    """Logic dự đoán dựa trên tần suất xuất hiện nhiều nhất trong dữ liệu quá khứ."""
    config = GAME_CONFIG.get(game_type)
    if not config:
        return []

    # Dự đoán cho Max 3D (Dạng chữ số)
    if config["type"] == "digit":
        if not history_data:
            return [random.randint(0, 9) for _ in range(config["length"])]
        
        # Lấy tần suất cho từng vị trí chữ số
        predicted = []
        for pos in range(config["length"]):
            digits_at_pos = [d["result"][pos] for d in history_data if len(d["result"]) > pos]
            if digits_at_pos:
                most_common_digit = Counter(digits_at_pos).most_common(1)[0][0]
                predicted.append(most_common_digit)
            else:
                predicted.append(random.randint(0, 9))
        return predicted

    # Dự đoán cho 6/55, 6/45, Keno (Dạng tập hợp số)
    if not history_data:
        return sorted(random.sample(range(1, config["max_num"] + 1), config["pick"]))

    all_numbers = [num for draw in history_data for num in draw.get("result", [])]
    freq = Counter(all_numbers)
    
    # Lấy các số xuất hiện nhiều nhất
    most_common = [num for num, _ in freq.most_common(config["pick"])]

    # Bổ sung số ngẫu nhiên nếu lịch sử chưa đủ mẫu
    while len(most_common) < config["pick"]:
        rand_n = random.randint(1, config["max_num"])
        if rand_n not in most_common:
            most_common.append(rand_n)

    return sorted(most_common)

def parse_date_range(raw_input: str) -> list:
    """Xử lý cú pháp ngày: YYYY-MM-DD hoặc YYYY-MM-DD => DD / YYYY-MM-DD => YYYY-MM-DD"""
    dates_to_test = []
    range_match = re.search(r'(\d{4}-\d{2}-\d{2})\s*(?:=>|->|-|\s+)\s*(\d{1,2}|\d{4}-\d{2}-\d{2})$', raw_input)
    
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
    elif re.match(r'^\d{4}-\d{2}-\d{2}$', raw_input):
        dates_to_test.append(raw_input)
        
    return dates_to_test

# --- TELEGRAM BOT HANDLERS ---
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    help_text = (
        "🤖 *BOT DỰ ĐOÁN & BACKTEST VIETLOTT*\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📌 *DANH SÁCH MÃ GIẢI:* \n"
        "• `655` : Power 6/55\n"
        "• `645` : Mega 6/45\n"
        "• `3d`  : Max 3D\n"
        "• `keno`: Keno\n\n"
        "🎯 *DỰ ĐOÁN KỲ TỚI:*\n"
        "▫️ `/dudoan <mã_giải>`\n"
        "  _Ví dụ:_ `/dudoan 655` hoặc `/dudoan keno`\n\n"
        "🧪 *BACKTEST (KIỂM THỬ THUẬT TOÁN):*\n"
        "▫️ `/test <mã_giải> <ngày>`\n"
        "▫️ `/test <mã_giải> <ngày_bắt_đầu> => <ngày_kết_thúc|ngày_cuối>`\n"
        "  _Ví dụ đơn ngày:_ `/test 655 2026-09-01`\n"
        "  _Ví dụ dải ngày:_ `/test 655 2026-08-25 => 2026-09-01`\n\n"
        "📊 *THỐNG KÊ CSDI:*\n"
        "▫️ `/thongke` : Xem số lượng kết quả đã lưu trữ"
    )
    bot.reply_to(message, help_text, parse_mode="Markdown")

@bot.message_handler(commands=['dudoan'])
def handle_prediction(message):
    args = message.text.strip().split()
    if len(args) < 2:
        bot.reply_to(message, "⚠️ Cú pháp chưa đúng! Dùng: `/dudoan <655|645|3d|keno>`", parse_mode="Markdown")
        return

    game = args[1].lower()
    if game not in GAME_CONFIG:
        bot.reply_to(message, "❌ Mã giải không hợp lệ! Chọn một trong các mã: `655`, `645`, `3d`, `keno`", parse_mode="Markdown")
        return

    history = [d for d in DATASET if d["game"] == game]
    predicted = predict_numbers(game, history)
    
    str_pred = ", ".join(map(str, predicted)) if isinstance(predicted, list) else str(predicted)

    report = (
        f"🎯 *DỰ ĐOÁN GIẢI {GAME_CONFIG[game]['name'].upper()}*\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 **Dàn số dự đoán kỳ tới:**\n`[{str_pred}]`\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 *Phân tích dựa trên thuật toán ma trận tần suất nhịp rơi.*"
    )
    bot.reply_to(message, report, parse_mode="Markdown")

@bot.message_handler(commands=['test'])
def handle_backtest(message):
    raw_text = message.text.strip()
    parts = raw_text.split(maxsplit=2)

    if len(parts) < 3:
        bot.reply_to(message, "⚠️ Cú pháp chưa đúng!\nVí dụ: `/test 655 2026-09-01` hoặc `/test 655 2026-08-25 => 01`", parse_mode="Markdown")
        return

    game = parts[1].lower()
    if game not in GAME_CONFIG:
        bot.reply_to(message, "❌ Mã giải không hợp lệ! Chọn: `655`, `645`, `3d`, `keno`", parse_mode="Markdown")
        return

    raw_date_input = parts[2]
    dates_to_test = parse_date_range(raw_date_input)

    if not dates_to_test:
        bot.reply_to(message, "❌ Định dạng ngày không hợp lệ. Dùng chuẩn YYYY-MM-DD", parse_mode="Markdown")
        return

    msg = bot.reply_to(message, f"⏳ Đang thực hiện Backtest giải **{GAME_CONFIG[game]['name']}** cho {len(dates_to_test)} ngày...", parse_mode="Markdown")

    valid_cnt = 0
    total_matches = 0
    total_possible = 0
    details_list = []

    for target_date_str in dates_to_test:
        try:
            target_date = datetime.strptime(target_date_str, "%Y-%m-%d")
        except ValueError:
            continue

        # 1. Lấy kết quả thực tế tại ngày test
        actual_draw = next((d for d in DATASET if d["game"] == game and d["date"] == target_date_str), None)
        if not actual_draw:
            continue

        # 2. Lọc dữ liệu LÙI VỀ TRƯỚC ngày test
        past_history = [
            d for d in DATASET 
            if d["game"] == game and datetime.strptime(d["date"], "%Y-%m-%d") < target_date
        ]

        # 3. Chạy thuật toán dự đoán chỉ dùng dữ liệu quá khứ
        predicted = predict_numbers(game, past_history)
        actual = actual_draw["result"]

        # 4. So sánh kết quả
        if GAME_CONFIG[game]["type"] == "digit":
            # So sánh vị trí chữ số chính xác (Max 3D)
            matched = [p for p, a in zip(predicted, actual) if p == a]
            match_cnt = len(matched)
            possible_cnt = len(actual)
        else:
            # So sánh tập hợp số trùng (6/55, 6/45, Keno)
            matched = list(set(predicted).intersection(set(actual)))
            match_cnt = len(matched)
            possible_cnt = len(actual)

        accuracy = (match_cnt / possible_cnt) * 100 if possible_cnt > 0 else 0
        valid_cnt += 1
        total_matches += match_cnt
        total_possible += possible_cnt

        str_pred = ",".join(map(str, predicted))
        str_actual = ",".join(map(str, actual))
        str_matched = ",".join(map(str, matched)) if matched else "Không"

        details_list.append(
            f"📅 **{target_date_str}**\n"
            f" └ Dự đoán: `[{str_pred}]` \n"
            f" └ Thực tế: `[{str_actual}]`\n"
            f" └ Trùng: `[{str_matched}]` (**{accuracy:.1f}%**)"
        )

    if valid_cnt == 0:
        bot.edit_message_text("❌ Không tìm thấy dữ liệu kết quả thực tế phù hợp trong dải ngày đã chọn.", chat_id=message.chat.id, message_id=msg.message_id)
        return

    overall_accuracy = (total_matches / total_possible) * 100 if total_possible > 0 else 0

    report_header = (
        f"🧪 *BÁO CÁO BACKTEST - {GAME_CONFIG[game]['name'].upper()}*\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
    )
    report_footer = (
        f"\n━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 **TỔNG KẾT HỆ THỐNG:**\n"
        f"• Số kỳ test thành công: `{valid_cnt}/{len(dates_to_test)}`\n"
        f"• Tổng số lượt trùng: `{total_matches}/{total_possible}` số\n"
        f"• **Độ chính xác trung bình:** `{overall_accuracy:.2f}%`"
    )

    full_report = report_header + "\n\n".join(details_list) + report_footer
    if len(full_report) > 4000:
        full_report = report_header + "\n\n".join(details_list[:10]) + f"\n\n... (ẩn {len(details_list)-10} kỳ) ..." + report_footer

    bot.edit_message_text(full_report, chat_id=message.chat.id, message_id=msg.message_id, parse_mode="Markdown")

@bot.message_handler(commands=['thongke'])
def handle_stats(message):
    total = len(DATASET)
    game_counts = Counter([d["game"] for d in DATASET])
    
    msg_lines = [f"📈 *THỐNG KÊ KHO DỮ LIỆU VIETLOTT*\n━━━━━━━━━━━━━━━━━━━━━\n• **Tổng bản ghi:** `{total}`"]
    for g, name_cfg in GAME_CONFIG.items():
        msg_lines.append(f"• **{name_cfg['name']}:** `{game_counts.get(g, 0)}` kỳ")
        
    bot.reply_to(message, "\n".join(msg_lines), parse_mode="Markdown")

# --- LUỒNG CHÍNH ĐIỀU HÀNH ---
if __name__ == '__main__':
    print("🚀 Khởi động Flask & Vietlott Telegram Bot...", flush=True)
    
    # 1. Chạy Flask Web Server ở luồng riêng
    threading.Thread(target=run_flask, daemon=True).start()

    # 2. Xóa Webhook cũ để tránh xung đột Polling
    try:
        bot.remove_webhook()
        time.sleep(1)
    except Exception as e:
        print(f"⚠️ Webhook warning: {e}", flush=True)

    print("🤖 Bot Telegram đang lắng nghe...", flush=True)

    # 3. Chạy Polling liên tục
    while True:
        try:
            bot.infinity_polling(skip_pending=True, timeout=20, long_polling_timeout=10)
        except Exception as e:
            print(f"⚠️ Polling retry: {e}", flush=True)
            time.sleep(5)
