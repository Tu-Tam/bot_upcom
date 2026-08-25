import os
import sys
import time
import threading
from datetime import datetime
import telebot
from flask import Flask

# Import các module nội bộ
import database as db
import scraper
import predictor

# Lấy Token từ Environment Variables trên Render
TOKEN = os.getenv("TELEGRAM_TOKEN")

# Kiểm tra an toàn biến môi trường
if not TOKEN:
    print("❌ LỖI FATAL: Chưa cấu hình TELEGRAM_TOKEN trong Environment Variables trên Render!", flush=True)
    print("👉 Hãy truy cập Render Dashboard -> Environment -> Thêm Key 'TELEGRAM_TOKEN'.", flush=True)
    sys.exit(1)

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# --- WEB SERVER GIỮ SERVICE LIVE TRÊN RENDER ---
@app.route('/')
def home():
    return "Bot Xổ Số MB đang chạy tốt!", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# --- BACKGROUND TASK: QUÉT DỮ LIỆU LỊCH SỬ ---
def fetch_initial_data():
    """Tự động cào dữ liệu 90 ngày gần nhất khi ứng dụng khởi động"""
    print("📦 Bắt đầu xây dựng kho dữ liệu 90 ngày...", flush=True)
    try:
        # Kiểm tra linh hoạt hàm có sẵn trong file scraper.py
        if hasattr(scraper, 'scrape_past_days'):
            scraper.scrape_past_days(90)
        elif hasattr(scraper, 'scrape_history'):
            scraper.scrape_history(90)
        elif hasattr(scraper, 'scrape_30_days'):
            scraper.scrape_30_days()
        elif hasattr(scraper, 'scrape_today'):
            scraper.scrape_today()
        else:
            print("⚠️ Không tìm thấy hàm cào lịch sử phù hợp trong scraper.py", flush=True)
            return
        print("✅ Đã hoàn tất khởi tạo kho dữ liệu!", flush=True)
    except Exception as e:
        print(f"⚠️ Lỗi khi khởi tạo dữ liệu: {e}", flush=True)

# --- TELEGRAM BOT HANDLERS ---
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    help_text = (
        "🤖 *BOT DỰ ĐOÁN XỔ SỐ MIỀN BẮC (XSMB)*\n\n"
        "Các câu lệnh khả dụng:\n"
        "🔹 `/dudoan` - Nhận dự đoán lô đẹp cho ngày hôm nay\n"
        "🔹 `/ketqua` - Xem kết quả XSMB mới nhất có trong CSDL\n"
        "🔹 `/capnhat` - Ép bot quét cập nhật kết quả hôm nay ngay lập tức\n"
        "🔹 `/thongke` - Trạng thái kho dữ liệu hiện tại\n"
        "🔹 `/help` - Xem lại hướng dẫn này"
    )
    bot.reply_to(message, help_text, parse_mode="Markdown")

@bot.message_handler(commands=['dudoan'])
def handle_prediction(message):
    msg = bot.reply_to(message, "⏳ Đang phân tích thuật toán thống kê, vui lòng đợi giây lát...")
    
    # Kiểm tra và tự cập nhật nếu thiếu dữ liệu mới
    today_str = datetime.now().strftime("%Y-%m-%d")
    recent = db.get_results(limit=1) if hasattr(db, 'get_results') else []
    if not recent or recent[0]['date'] != today_str:
        if hasattr(scraper, 'scrape_today'):
            scraper.scrape_today()

    results = db.get_full(limit=90) if hasattr(db, 'get_full') else []
    if not results:
        bot.edit_message_text("⚠️ Chưa có đủ dữ liệu trong CSDL để phân tích. Hãy thử `/capnhat` trước!", 
                              chat_id=message.chat.id, message_id=msg.message_id)
        return

    pred_text = predictor.generate_prediction_report(results)
    bot.edit_message_text(pred_text, chat_id=message.chat.id, message_id=msg.message_id, parse_mode="Markdown")

@bot.message_handler(commands=['ketqua'])
def handle_latest_result(message):
    results = db.get_results(limit=1) if hasattr(db, 'get_results') else []
    if not results:
        bot.reply_to(message, "⚠️ Chưa có dữ liệu kết quả nào trong CSDL.")
        return
    
    latest = results[0]
    date_str = latest.get('date', 'N/A')
    nums = latest.get('numbers', [])
    
    if not nums:
        bot.reply_to(message, f"📅 Ngày `{date_str}`: Chưa có kết quả.", parse_mode="Markdown")
        return
        
    db_val = nums[0] if len(nums) > 0 else "---"
    g1_val = nums[1] if len(nums) > 1 else "---"
    lotto_list = ", ".join(nums[1:]) if len(nums) > 1 else "Không có"
    
    res_msg = (
        f"📊 *KẾT QUẢ XSMB NGÀY {date_str}*\n\n"
        f"🏆 **Giải Đặc Biệt:** `{db_val}`\n"
        f"🥇 **Giải Nhất:** `{g1_val}`\n"
        f"🎲 **Lô tô về ({len(nums)} giải):**\n`{lotto_list}`"
    )
    bot.reply_to(message, res_msg, parse_mode="Markdown")

@bot.message_handler(commands=['capnhat'])
def handle_manual_update(message):
    msg = bot.reply_to(message, "🔍 Đang tiến hành quét kết quả XSMB mới nhất...")
    success = scraper.scrape_today() if hasattr(scraper, 'scrape_today') else False
    if success:
        bot.edit_message_text("✅ Đã cập nhật thành công kết quả mới nhất vào CSDL!", 
                              chat_id=message.chat.id, message_id=msg.message_id)
    else:
        bot.edit_message_text("⚠️ Không tìm thấy kết quả mới hoặc chưa đến giờ quay thưởng (18h15).", 
                              chat_id=message.chat.id, message_id=msg.message_id)

@bot.message_handler(commands=['thongke'])
def handle_stats(message):
    count = db.count_results() if hasattr(db, 'count_results') else 0
    min_date, max_date = db.get_date_range() if hasattr(db, 'get_date_range') else (None, None)
    
    stats_msg = (
        "📈 *THỐNG KÊ KHO DỮ LIỆU CSDL*\n\n"
        f"▫️ **Tổng số ngày đã lưu:** `{count}` ngày\n"
        f"▫️ **Ngày dữ liệu cũ nhất:** `{min_date or 'N/A'}`\n"
        f"▫️ **Ngày dữ liệu mới nhất:** `{max_date or 'N/A'}`"
    )
    bot.reply_to(message, stats_msg, parse_mode="Markdown")

# --- LUỒNG CHÍNH (MAIN EXECUTION) ---
if __name__ == '__main__':
    print("🚀 Khởi động Flask & Bot Telegram...", flush=True)
    
    # 1. Chạy Web Server trong Thread riêng để Render giữ service live
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # 2. Chạy tiến trình cào dữ liệu lịch sử trong Thread riêng
    data_thread = threading.Thread(target=fetch_initial_data, daemon=True)
    data_thread.start()

    # 3. Dọn dẹp Webhook chuẩn cho pyTelegramBotAPI
    try:
        bot.remove_webhook()
    except Exception as e:
        print(f"⚠️ Lỗi dọn dẹp Webhook: {e}", flush=True)

    # Bỏ qua tin nhắn cũ tồn đọng khi ngắt kết nối
    bot.skip_pending = True

    print("🤖 Bot đang lắng nghe lệnh...", flush=True)

    # 4. Vòng lặp Polling an toàn
    while True:
        try:
            bot.infinity_polling(timeout=20, long_polling_timeout=10)
        except Exception as e:
            print(f"⚠️ Lỗi hệ thống Polling: {e}", flush=True)
            time.sleep(3)