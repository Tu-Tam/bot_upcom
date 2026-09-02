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

# --- CƠ SỞ DỮ LIỆU LỊCH SỬ MỞ RỘNG ---
DATASET = [
    # Power 6/55 (Dữ liệu nhiều kỳ để tính chính xác)
    {"date": "2026-08-01", "game": "655", "result": [3, 11, 22, 34, 41, 50]},
    {"date": "2026-08-04", "game": "655", "result": [7, 12, 19, 28, 35, 49]},
    {"date": "2026-08-06", "game": "655", "result": [2, 15, 24, 30, 42, 53]},
    {"date": "2026-08-08", "game": "655", "result": [9, 18, 21, 33, 40, 55]},
    {"date": "2026-08-11", "game": "655", "result": [5, 12, 27, 31, 38, 44]},
    {"date": "2026-08-13", "game": "655", "result": [1, 14, 20, 29, 43, 52]},
    {"date": "2026-08-15", "game": "655", "result": [6, 17, 25, 36, 41, 48]},
    {"date": "2026-08-18", "game": "655", "result": [10, 12, 23, 32, 39, 51]},
    {"date": "2026-08-20", "game": "655", "result": [4, 16, 28, 30, 45, 54]},
    {"date": "2026-08-22", "game": "655", "result": [8, 13, 21, 37, 40, 47]},
    {"date": "2026-08-25", "game": "655", "result": [4, 12, 18, 27, 39, 48]},
    {"date": "2026-08-27", "game": "655", "result": [2, 12, 21, 35, 42, 51]},
    {"date": "2026-08-29", "game": "655", "result": [8, 15, 18, 29, 33, 45]},
    {"date": "2026-09-01", "game": "655", "result": [2, 12, 18, 28, 40, 52]},
    # Mega 6/45
    {"date": "2026-08-21", "game": "645", "result": [3, 10, 18, 25, 32, 42]},
    {"date": "2026-08-23", "game": "645", "result": [7, 12, 20, 29, 35, 44]},
    {"date": "2026-08-26", "game": "645", "result": [5, 11, 23, 31, 38, 41]},
    {"date": "2026-08-28", "game": "645", "result": [1, 11, 19, 23, 34, 40]},
    {"date": "2026-08-30", "game": "645", "result": [5, 14, 23, 30, 39, 44]},
    # Max 3D
    {"date": "2026-08-31", "game": "3d", "result": [3, 8, 5]},
    {"date": "2026-09-01", "game": "3d", "result": [7, 2, 9]},
    # Keno
    {"date": "2026-09-01", "game": "keno", "result": [3, 7, 12, 15, 18, 22, 25, 31, 34, 39, 41, 45, 50, 53, 58, 62, 67, 71, 75, 79]},
]

# --- THUẬT TOÁN TÍNH TOÁN TRỌNG SỐ ĐA TẦNG ---
def predict_numbers(game_type: str, history_data: list) -> list:
    config = GAME_CONFIG.get(game_type)
    if not config:
        return []

    # 1. Dự đoán Max 3D (Dạng vị trí chữ số)
    if config["type"] == "digit":
        if not history_data:
            return [random.randint(0, 9) for _ in range(config["length"])]
        predicted = []
        for pos in range(config["length"]):
            digits = [d["result"][pos] for d in history_data if len(d["result"]) > pos]
            if digits:
                # Tính điểm trọng số giảm dần theo thời gian (kỳ gần điểm cao hơn)
                scores = {d: 0.0 for d in range(10)}
                for i, val in enumerate(reversed(digits)):
                    scores[val] += 1.0 / (i + 1)
                best_digit = max(scores, key=scores.get)
                predicted.append(best_digit)
            else:
                predicted.append(random.randint(0, 9))
        return predicted

    # 2. Dự đoán 6/55, 6/45, Keno bằng thuật toán Trọng số
    pick_count = config["pick"]
    max_num = config["max_num"]

    if len(history_data) < 2:
        nums = list(range(1, max_num + 1))
        random.shuffle(nums)
        return sorted(nums[:pick_count])

    scores = {n: 0.0 for n in range(1, max_num + 1)}

    # A. Tính điểm Tần suất & Nhịp rơi (Recency Decay)
    for idx, draw in enumerate(reversed(history_data)):
        weight = 1.0 / (idx + 1)  # Kỳ càng gần trọng số càng cao
        for num in draw.get("result", []):
            if 1 <= num <= max_num:
                scores[num] += weight * 10.0

    # B. Tính điểm Lô Gan (Số lâu chưa về)
    last_seen = {}
    for idx, draw in enumerate(reversed(history_data)):
        for num in draw.get("result", []):
            if num not in last_seen:
                last_seen[num] = idx

    for n in range(1, max_num + 1):
        gap = last_seen.get(n, len(history_data))
        if 3 <= gap <= 8:  # Nhịp rơi lý tưởng của xổ số
            scores[n] += 5.0
        elif gap > 10:     # Lô gan đạt ngưỡng bùng nổ
            scores[n] += 3.0

    # C. Sắp xếp danh sách theo điểm số từ cao xuống thấp
    ranked_numbers = sorted(scores.keys(), key=lambda n: scores[n], reverse=True)
    
    # D. Bộ lọc Cân bằng Chẵn/Lẻ (Ưu tiên tỷ lệ 3:3 hoặc 4:2)
    selected = []
    even_count = 0
    odd_count = 0
    max_parity = (pick_count // 2) + 1  # Tối đa 4 số chẵn hoặc 4 số lẻ

    for num in ranked_numbers:
        if len(selected) == pick_count:
            break
        if num % 2 == 0 and even_count < max_parity:
            selected.append(num)
            even_count += 1
        elif num % 2 != 0 and odd_count < max_parity:
            selected.append(num)
            odd_count += 1

    # Bổ sung nếu chưa đủ bộ số
    for num in ranked_numbers:
        if len(selected) == pick_count:
            break
        if num not in selected:
            selected.append(num)

    return sorted(selected)

def parse_date_range(raw_input: str) -> list:
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
        "🤖 *BOT DỰ ĐOÁN & BACKTEST VIETLOTT (MÔ HÌNH TRỌNG SỐ)*\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📌 *DANH SÁCH MÃ GIẢI:* \n"
        "• `655` : Power 6/55\n"
        "• `645` : Mega 6/45\n"
        "• `3d`  : Max 3D\n"
        "• `keno`: Keno\n\n"
        "🎯 *DỰ ĐOÁN KỲ TỚI:*\n"
        "▫️ `/dudoan <mã_giải>`\n"
        "  _Ví dụ:_ `/dudoan 655`\n\n"
        "🧪 *BACKTEST THUẬT TOÁN:*\n"
        "▫️ `/test <mã_giải> <ngày>`\n"
        "  _Ví dụ:_ `/test 655 2026-08-29`\n\n"
        "📊 *THỐNG KÊ KHO DỮ LIỆU:*\n"
        "▫️ `/thongke`"
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
        bot.reply_to(message, "❌ Mã giải không hợp lệ!", parse_mode="Markdown")
        return

    history = [d for d in DATASET if d["game"] == game]
    predicted = predict_numbers(game, history)
    str_pred = ", ".join(map(str, predicted))

    report = (
        f"🎯 *DỰ ĐOÁN GIẢI {GAME_CONFIG[game]['name'].upper()}*\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 **Dàn số tối ưu kỳ tới:**\n`[{str_pred}]`\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 *Phân tích bằng Thuật toán Ma trận Trọng số Đa tầng & Cân bằng Chẵn/Lẻ.*"
    )
    bot.reply_to(message, report, parse_mode="Markdown")

@bot.message_handler(commands=['test'])
def handle_backtest(message):
    raw_text = message.text.strip()
    parts = raw_text.split(maxsplit=2)

    if len(parts) < 3:
        bot.reply_to(message, "⚠️ Cú pháp: `/test 655 2026-08-29`", parse_mode="Markdown")
        return

    game = parts[1].lower()
    if game not in GAME_CONFIG:
        bot.reply_to(message, "❌ Mã giải không hợp lệ!", parse_mode="Markdown")
        return

    raw_date_input = parts[2]
    dates_to_test = parse_date_range(raw_date_input)

    msg = bot.reply_to(message, f"⏳ Đang thực hiện Backtest giải **{GAME_CONFIG[game]['name']}**...", parse_mode="Markdown")

    available_draws = sorted(
        [d for d in DATASET if d["game"] == game],
        key=lambda x: datetime.strptime(x["date"], "%Y-%m-%d")
    )

    if not available_draws:
        bot.edit_message_text("❌ Chưa có dữ liệu lịch sử cho giải này.", chat_id=message.chat.id, message_id=msg.message_id)
        return

    valid_cnt = 0
    total_matches = 0
    total_possible = 0
    details_list = []

    for target_date_str in dates_to_test:
        try:
            target_date = datetime.strptime(target_date_str, "%Y-%m-%d")
        except ValueError:
            continue

        actual_draw = next((d for d in available_draws if d["date"] == target_date_str), None)
        note_next_day = ""

        if not actual_draw:
            next_draws = [d for d in available_draws if datetime.strptime(d["date"], "%Y-%m-%d") > target_date]
            if next_draws:
                actual_draw = next_draws[0]
                note_next_day = f" _(Tự chuyển sang kỳ kế tiếp: {actual_draw['date']})_"
            else:
                continue

        actual_date_str = actual_draw["date"]
        actual_date_obj = datetime.strptime(actual_date_str, "%Y-%m-%d")

        past_history = [
            d for d in DATASET 
            if d["game"] == game and datetime.strptime(d["date"], "%Y-%m-%d") < actual_date_obj
        ]

        predicted = predict_numbers(game, past_history)
        actual = actual_draw["result"]

        if GAME_CONFIG[game]["type"] == "digit":
            matched = [p for p, a in zip(predicted, actual) if p == a]
        else:
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
            f"📅 **Yêu cầu: {target_date_str}**{note_next_day}\n"
            f" └ Kết quả kỳ {actual_date_str}: `[{str_actual}]`\n"
            f" └ Dự đoán tối ưu: `[{str_pred}]`\n"
            f" └ Trùng khớp: `[{str_matched}]` (**{accuracy:.1f}%**)"
        )

    if valid_cnt == 0:
        bot.edit_message_text("❌ Ngày bạn nhập vượt quá dữ liệu hiện có.", chat_id=message.chat.id, message_id=msg.message_id)
        return

    overall_accuracy = (total_matches / total_possible) * 100 if total_possible > 0 else 0

    report_header = (
        f"🧪 *BÁO CÁO BACKTEST TRỌNG SỐ - {GAME_CONFIG[game]['name'].upper()}*\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
    )
    report_footer = (
        f"\n━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 **TỔNG KẾT HỆ THỐNG:**\n"
        f"• Số kỳ test thành công: `{valid_cnt}`\n"
        f"• Tổng số lượt trùng: `{total_matches}/{total_possible}` số\n"
        f"• **Độ chính xác trung bình:** `{overall_accuracy:.2f}%`"
    )

    full_report = report_header + "\n\n".join(details_list) + report_footer
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