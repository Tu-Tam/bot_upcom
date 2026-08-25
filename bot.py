import os
import re
import json
import time
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from threading import Thread, Lock
from flask import Flask
import telebot
from telebot import apihelper
import requests

# === NHẬP CSDL ===
from database import (
    init_db, save_result, get_results, get_date_range,
    count_results
)
from scraper import tai_90_ngay_gan_nhat
from predictor import predict

# Biến khóa luồng CSDL tránh ghi đè/xung đột SQLite
db_lock = Lock()

# === WEB GIỮ SỐNG ===
app = Flask(__name__)

@app.route('/')
def keep_alive():
    try:
        total = count_results()
        min_date, max_date = get_date_range()
        return (
            f"✅ Bot XSMB ĐANG CHẠY ỔN!\n"
            f"📂 Dữ liệu: {total} ngày\n"
            f"📅 Khoảng: {min_date or '—'} → {max_date or '—'}"
        )
    except Exception:
        return "🤖 Bot hoạt động — Dữ liệu đang được chuẩn bị..."

# === TOKEN & CONFIG ===
BOT_TOKEN = os.environ.get(
    "BOT_TOKEN",
    "8520938638:AAF3KD6Qj8k7nPLaq8uJs25ZhSw_D8OTCY0"
)
CHAT_ID = int(os.environ.get("CHAT_ID", "7064473358"))

bot = telebot.TeleBot(BOT_TOKEN)

# === HANDLERS ===
@bot.message_handler(commands=['start', 'help'])
def cmd_start(message):
    bot.send_message(
        message.chat.id,
        "🤖 BOT XỔ SỐ MIỀN BẮC TỰ ĐỘNG:\n"
        "/stats — Trạng thái dữ liệu\n"
        "/top3 [YYYY-MM-DD] — Dự đoán đuôi mạnh nhất\n"
        "/top10 [YYYY-MM-DD] — Danh sách 10 số\n"
        "/backtest [số_ngày] — Kiểm chứng độ chính xác\n"
        "/update — Tải cập nhật lịch sử & ngày mới"
    )

@bot.message_handler(commands=['stats'])
def cmd_stats(message):
    try:
        init_db()
        total = count_results()
        min_d, max_d = get_date_range()
        bot.send_message(
            message.chat.id,
            f"📂 THÔNG TIN DỮ LIỆU:\n"
            f"• Tổng ngày: {total}\n"
            f"• Từ: {min_d or 'chưa có'}\n"
            f"• Đến: {max_d or 'chưa có'}"
        )
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Lỗi: {str(e)}")

@bot.message_handler(commands=['top3'])
def cmd_top3(message):
    args = message.text.split()
    target_date = datetime.now().strftime("%Y-%m-%d")
    if len(args) >= 2:
        target_date = args[1]
    try:
        top_list = predict(target_date, limit=3)
        text = f"🎯 TOP 3 NGÀY {target_date}:\n"
        for idx, (num, score) in enumerate(top_list, 1):
            text += f"{idx}. {num} — điểm: {score:.3f}\n"
        bot.send_message(message.chat.id, text)
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Không tính được: {str(e)}")

@bot.message_handler(commands=['top10'])
def cmd_top10(message):
    args = message.text.split()
    target_date = datetime.now().strftime("%Y-%m-%d")
    if len(args) >= 2:
        target_date = args[1]
    try:
        top_list = predict(target_date, limit=10)
        text = f"📋 TOP 10 NGÀY {target_date}:\n"
        for idx, (num, score) in enumerate(top_list, 1):
            text += f"{idx:2d}. {num} — {score:.3f}\n"
        bot.send_message(message.chat.id, text)
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Lỗi: {str(e)}")

@bot.message_handler(commands=['backtest'])
def cmd_backtest(message):
    args = message.text.split()
    days = 30
    if len(args) >= 2 and args[1].isdigit():
        days = int(args[1])
    bot.send_message(message.chat.id, f"🔍 Đang kiểm chứng {days} ngày... vui lòng chờ!")
    try:
        from backtest import run_backtest, summarize
        result_list = run_backtest(days)
        summary = summarize(result_list)
        txt = (
            f"📊 KẾT QUẢ KIỂM CHỨNG {summary.get('days', 0)} NGÀY:\n"
            f"✅ Trúng: {summary.get('hits')} / {summary.get('days')}\n"
            f"🎯 Tỷ lệ chung: {summary.get('hit_rate',0)*100:.2f}%\n"
            f"🥇 Top1: {summary.get('top1',0)*100:.2f}% | 🥉 Top3: {summary.get('top3',0)*100:.2f}%\n"
            f"📌 Top10: {summary.get('top10',0)*100:.2f}%"
        )
        bot.send_message(message.chat.id, txt)
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Lỗi kiểm tra: {repr(e)}")

@bot.message_handler(commands=['update'])
def cmd_update(message):
    bot.send_message(message.chat.id, "🔄 Đang quét & cập nhật CSDL... chờ lát nhé!")
    def background():
        with db_lock:
            try:
                init_db()
                ok = tai_90_ngay_gan_nhat()
                bot.send_message(
                    message.chat.id,
                    f"✅ Hoàn tất cập nhật! Hiện có {ok} ngày chuẩn trong kho."
                )
            except Exception as e:
                bot.send_message(message.chat.id, f"❌ Lỗi cập nhật: {str(e)}")
    Thread(target=background, daemon=True).start()

# === MAIN RUNNER ===
if __name__ == "__main__":
    init_db()
    print("🚀 Khởi động Flask & Bot Telegram...")

    # Tiến trình khởi tạo dữ liệu chạy ngầm + Báo tin nhắn Telegram
    def khoi_tao_du_lieu():
        with db_lock:
            try:
                print("📦 Bắt đầu xây dựng kho dữ liệu 90 ngày...")
                so_ngay = tai_90_ngay_gan_nhat()
                print(f"✅ Đã xây dựng xong: {so_ngay} ngày hợp lệ!")
                
                # Tự động gửi thông báo về Telegram khi sẵn sàng
                if CHAT_ID:
                    bot.send_message(
                        CHAT_ID,
                        f"🚀 **BOT XSMB ĐÃ KHỞI ĐỘNG CẢI TIẾN!**\n"
                        f"📂 Dữ liệu sẵn sàng: {so_ngay} ngày.\n"
                        f"Gõ /stats hoặc /help để kiểm tra."
                    )
            except Exception as err:
                print(f"⚠️ Quá trình nền gặp lỗi: {err}")

    Thread(target=khoi_tao_du_lieu, daemon=True).start()

    # Web Server
    def run_web():
        cong = int(os.environ.get("PORT", 8080))
        app.run(host="0.0.0.0", port=cong, use_reloader=False)

    Thread(target=run_web, daemon=True).start()

    print("🤖 Bot đang lắng nghe lệnh...")

    # Vòng lặp Polling chuẩn cú pháp telebot
    while True:
        try:
            bot.remove_webhook()
            bot.skip_pending()  # Bỏ qua tin nhắn cũ đọng lại
            time.sleep(2)
            
            bot.infinity_polling(
                timeout=30,
                long_polling_timeout=20,
                none_stop=True
            )
        except apihelper.ApiTelegramException as e:
            if '409' in str(e):
                print("Lỗi 409: Trùng lặp Polling. Chờ 20s xả phiên...")
                time.sleep(20)
            else:
                print("Lỗi Telegram API:", e)
                time.sleep(5)
        except Exception as e:
            print("Lỗi hệ thống Polling:", e)
            time.sleep(5)