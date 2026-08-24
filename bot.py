import os
from flask import Flask
import telebot
from datetime import datetime

# Nạp module nội bộ — KHỚP HOÀN HẢO
from config import DATABASE_PATH
from database import init_db, count_results, get_date_range
from scraper import fetch_and_parse_all
from predictor import predict
from backtest import run_backtest, summarize

# ---------- WEB SERVER GIỮ UPTIME RENDER ----------
app = Flask(__name__)

@app.route('/')
def home():
    try:
        total = count_results()
        min_d, max_d = get_date_range()
        return (
            f"✅ Bot XSMB HOẠT ĐỘNG!\n"
            f"📂 Dữ liệu: {total} ngày\n"
            f"📅 Khoảng: {min_d} → {max_d}"
        )
    except Exception:
        return "🤖 Bot đang chạy, vui lòng /update để tạo dữ liệu."


# ---------- TOKEN & ID: Ưu tiên biến môi trường Render + mặc định an toàn ----------
BOT_TOKEN = os.environ.get(
    "BOT_TOKEN",
    "8520938638:AAEHwQp89_P2slG7YTkod4z6_XvYbgBD7ns"
)
CHAT_ID = int(os.environ.get("CHAT_ID", "7064473358"))

bot = telebot.TeleBot(BOT_TOKEN)


# ---------- LỆNH /start ----------
@bot.message_handler(commands=['start'])
def cmd_start(msg):
    bot.send_message(
        msg.chat.id,
        "🤖 Bot XỔ SỐ MIỀN BẮC HOÀN CHỈNH:\n"
        "/update — Tải & cập nhật dữ liệu đầy đủ\n"
        "/top3 [YYYY-MM-DD] — Dự đoán 3 đuôi mạnh nhất\n"
        "/top10 [YYYY-MM-DD] — Danh sách chi tiết 10 số\n"
        "/backtest [số_ngày] — Kiểm chứng độ chính xác\n"
        "/stats — Xem tình trạng cơ sở dữ liệu"
    )


# ---------- LỆNH /update ----------
@bot.message_handler(commands=['update'])
def cmd_update(msg):
    bot.send_message(msg.chat.id, "🔄 Đang quét nguồn & lưu CSDL... vui chờ!")
    try:
        init_db()
        data = fetch_and_parse_all()
        bot.send_message(
            msg.chat.id,
            f"✅ Hoàn tất! Đã xử lý: {len(data)} bản ghi ngày."
        )
    except Exception as e:
        bot.send_message(msg.chat.id, f"❌ Lỗi: {str(e)}")


# ---------- LỆNH /top3 ----------
@bot.message_handler(commands=['top3'])
def cmd_top3(msg):
    parts = msg.text.strip().split()
    target = datetime.now().strftime("%Y-%m-%d")
    if len(parts) >= 2:
        target = parts[1]
    try:
        lst = predict(target, top_n=3)
        txt = f"🎯 TOP 3 — NGÀY: {target}\n"
        for i, (num, sc) in enumerate(lst, 1):
            txt += f"{i}. {num} | điểm={sc:.4f}\n"
        bot.send_message(msg.chat.id, txt)
    except Exception as e:
        bot.send_message(msg.chat.id, f"❌ {str(e)}")


# ---------- LỆNH /top10 ----------
@bot.message_handler(commands=['top10'])
def cmd_top10(msg):
    parts = msg.text.strip().split()
    target = datetime.now().strftime("%Y-%m-%d")
    if len(parts) >= 2:
        target = parts[1]
    try:
        lst = predict(target, top_n=10)
        txt = f"📋 TOP 10 — NGÀY: {target}\n"
        for i, (num, sc) in enumerate(lst, 1):
            txt += f"{i:2d}. {num} | điểm={sc:.4f}\n"
        bot.send_message(msg.chat.id, txt)
    except Exception as e:
        bot.send_message(msg.chat.id, f"❌ {str(e)}")


# ---------- LỆNH /backtest ----------
@bot.message_handler(commands=['backtest'])
def cmd_bt(msg):
    parts = msg.text.strip().split()
    n = 30
    if len(parts) >= 2 and parts[1].isdigit():
        n = int(parts[1])
    bot.send_message(msg.chat.id, f"🔍 Chạy kiểm chứng {n} ngày... hơi lâu nhé!")
    try:
        kq = run_backtest(n)
        st = summarize(kq)
        txt = (
            f"📊 TỔNG HỢP: {st.get('days',0)} ngày\n"
            f"✅ Trúng: {st.get('hits')} | Tỷ lệ: {st.get('hit_rate',0)*100:.2f}%\n"
            f"🥇 Top1: {st.get('top1',0)*100:.2f}% | 🥉 Top3: {st.get('top3',0)*100:.2f}%\n"
            f"📌 Top5: {st.get('top5',0)*100:.2f}% | 📎 Top10: {st.get('top10',0)*100:.2f}%"
        )
        bot.send_message(msg.chat.id, txt)
    except Exception as e:
        bot.send_message(msg.chat.id, f"❌ Lỗi kiểm tra: {repr(e)}")


# ---------- LỆNH /stats ----------
@bot.message_handler(commands=['stats'])
def cmd_stats(msg):
    try:
        init_db()
        n = count_results()
        mn, mx = get_date_range()
        bot.send_message(
            msg.chat.id,
            f"📂 DỮ LIỆU HIỆN CÓ:\n- Tổng ngày: {n}\n- Từ {mn} → {mx}"
        )
    except Exception as e:
        bot.send_message(msg.chat.id, f"❌ {str(e)}")


# ---------- KHỞI ĐỘNG CHÍNH THỨC ----------
if __name__ == "__main__":
    from threading import Thread
    init_db()
    print("🚀 Flask + Bot Telegram đang khởi động...")

    # Web giữ mạng
    def web_run():
        port = int(os.environ.get("PORT", 8080))
        app.run(host="0.0.0.0", port=port)

    Thread(target=web_run, daemon=True).start()

    # Vòng lặp Bot ổn định cho Render
    print("🤖 Bot đang lắng nghe...")
    bot.infinity_polling(timeout=25, interval=1)
