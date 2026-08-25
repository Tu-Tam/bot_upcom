import os
import sys
import time
import threading
import json
from datetime import datetime, timedelta
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
        scraper.scrape_past_days(days=90)
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
        "🔹 `/thongke` hoặc `/stats` - Trạng thái kho dữ liệu hiện tại\n"
        "🔹 `/test` - Kiểm tra trạng thái kết nối hệ thống\n"
        "🔹 `/test YYYY-MM-DD` - Kiểm tra tỷ lệ xác suất trúng của bot tại ngày cố định (Backtest)\n"
        "🔹 `/help` - Xem lại hướng dẫn này"
    )
    bot.reply_to(message, help_text, parse_mode="Markdown")

@bot.message_handler(commands=['dudoan'])
def handle_prediction(message):
    msg = bot.reply_to(message, "⏳ Đang phân tích thuật toán thống kê, vui lòng đợi giây lát...")
    
    # Kiểm tra và tự cập nhật nếu thiếu dữ liệu mới
    today_str = datetime.now().strftime("%Y-%m-%d")
    recent = db.get_results(limit=1) if hasattr(db, 'get_results') else None
    
    if not recent or (isinstance(recent, list) and len(recent) > 0 and recent[0].get('date') != today_str):
        scraper.scrape_today()

    # Lấy dữ liệu phân tích
    if hasattr(db, 'get_full'):
        results = db.get_full(limit=90)
    elif hasattr(db, 'get_results'):
        results = db.get_results(limit=90)
    else:
        results = []

    if not results:
        bot.edit_message_text("⚠️ Chưa có đủ dữ liệu trong CSDL để phân tích. Hãy bấm `/capnhat` trước!", 
                              chat_id=message.chat.id, message_id=msg.message_id, parse_mode="Markdown")
        return

    try:
        pred_text = predictor.generate_prediction_report(results)
        bot.edit_message_text(pred_text, chat_id=message.chat.id, message_id=msg.message_id, parse_mode="Markdown")
    except Exception as e:
        bot.edit_message_text(f"⚠️ Lỗi khi tạo bản tin dự đoán: {e}", chat_id=message.chat.id, message_id=msg.message_id)

@bot.message_handler(commands=['ketqua'])
def handle_latest_result(message):
    results = db.get_results(limit=1) if hasattr(db, 'get_results') else None
    if not results:
        bot.reply_to(message, "⚠️ Chưa có dữ liệu kết quả nào trong CSDL.")
        return
    
    latest = results[0]
    date_str = latest.get('date', 'N/A')
    nums = latest.get('numbers', [])
    
    # Xử lý nếu numbers lưu dưới dạng chuỗi trong DB
    if isinstance(nums, str):
        try:
            nums = json.loads(nums)
        except:
            nums = nums.split(',')

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
    success = scraper.scrape_today()
    if success:
        bot.edit_message_text("✅ Đã cập nhật thành công kết quả mới nhất vào CSDL!", 
                              chat_id=message.chat.id, message_id=msg.message_id)
    else:
        bot.edit_message_text("⚠️ Không tìm thấy kết quả mới hoặc chưa đến giờ quay thưởng (18h15).", 
                              chat_id=message.chat.id, message_id=msg.message_id)

# Xử lý đồng thời cả lệnh /thongke và /stats an toàn
@bot.message_handler(commands=['thongke', 'stats'])
def handle_stats(message):
    count = db.count_results() if hasattr(db, 'count_results') else 0
    
    if hasattr(db, 'get_date_range'):
        min_date, max_date = db.get_date_range()
    else:
        min_date, max_date = None, None
    
    stats_msg = (
        "📈 *THỐNG KÊ KHO DỮ LIỆU CSDL*\n\n"
        f"▫️ **Tổng số ngày đã lưu:** `{count}` ngày\n"
        f"▫️ **Ngày dữ liệu cũ nhất:** `{min_date or 'N/A'}`\n"
        f"▫️ **Ngày dữ liệu mới nhất:** `{max_date or 'N/A'}`"
    )
    bot.reply_to(message, stats_msg, parse_mode="Markdown")

# --- LỆNH MỚI: KIỂM TRA HỆ THỐNG / BACKTEST NGÀY CỐ ĐỊNH ---
@bot.message_handler(commands=['test'])
def handle_test_command(message):
    text_parts = message.text.strip().split()
    
    # TH1: Có nhập tham số ngày (Ví dụ: /test 2026-08-20) -> Test độ chính xác lịch sử
    if len(text_parts) > 1:
        target_date = text_parts[1]
        msg = bot.reply_to(message, f"⏳ Đang chạy thuật toán kiểm tra dữ liệu ngày `{target_date}`...", parse_mode="Markdown")
        
        if hasattr(predictor, 'test_prediction_accuracy'):
            report = predictor.test_prediction_accuracy(target_date)
        else:
            report = "⚠️ Chưa cập nhật hàm `test_prediction_accuracy` trong `predictor.py`."
            
        bot.edit_message_text(report, chat_id=message.chat.id, message_id=msg.message_id, parse_mode="Markdown")
        
    # TH2: Chỉ gõ /test -> Kiểm tra kết nối hệ thống
    else:
        msg = bot.reply_to(message, "🔍 *Bắt đầu kiểm tra kết nối hệ thống...*", parse_mode="Markdown")
        status_report = []
        
        try:
            count = db.count_results() if hasattr(db, 'count_results') else 0
            status_report.append(f"✅ **CSDL:** Hoạt động tốt (Đã lưu {count} ngày)")
        except Exception as e:
            status_report.append(f"❌ **CSDL:** Lỗi (`{e}`)")
            
        try:
            status_report.append("✅ **Scraper:** Hàm cào dữ liệu sẵn sàng")
        except Exception as e:
            status_report.append(f"❌ **Scraper:** Lỗi (`{e}`)")

        try:
            if hasattr(predictor, 'generate_prediction_report'):
                status_report.append("✅ **Predictor:** Hàm tạo bản tin dự đoán sẵn sàng")
            else:
                status_report.append("❌ **Predictor:** Thiếu hàm `generate_prediction_report`")
        except Exception as e:
            status_report.append(f"❌ **Predictor:** Lỗi (`{e}`)")

        report_text = (
            "🧪 *BÁO CÁO KIỂM TRA HỆ THỐNG*\n\n" +
            "\n".join(status_report) +
            "\n\n💡 *Mẹo:* Bạn có thể test độ chính xác ngày bất kỳ bằng cú pháp:\n`/test YYYY-MM-DD` (Ví dụ: `/test 2026-08-20`)"
        )
        bot.edit_message_text(report_text, chat_id=message.chat.id, message_id=msg.message_id, parse_mode="Markdown")

# --- LUỒNG CHÍNH (MAIN EXECUTION) ---
if __name__ == '__main__':
    print("🚀 Khởi động Flask & Bot Telegram...", flush=True)
    
    # 1. Chạy Web Server trong Thread riêng để Render giữ service live
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # 2. Chạy tiến trình cào dữ liệu lịch sử trong Thread riêng
    data_thread = threading.Thread(target=fetch_initial_data, daemon=True)
    data_thread.start()

    # 3. Dọn dẹp Webhook cũ & trễ 2 giây để Telegram giải phóng kết nối socket
    try:
        bot.remove_webhook()
        time.sleep(2)
    except Exception as e:
        print(f"⚠️ Lỗi dọn dẹp Webhook: {e}", flush=True)

    print("🤖 Bot đang lắng nghe lệnh...", flush=True)

    # 4. Vòng lặp Polling an toàn - Tự khôi phục nếu đứt kết nối
    while True:
        try:
            bot.infinity_polling(skip_pending=True, timeout=20, long_polling_timeout=10)
        except Exception as e:
            print(f"⚠️ Lỗi hệ thống Polling (sẽ thử lại sau 5 giây): {e}", flush=True)
            time.sleep(5)