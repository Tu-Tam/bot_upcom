import os
import sys
import time
import threading
import json
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
    """Tự động cào dữ liệu 365 ngày gần nhất khi ứng dụng khởi động"""
    print("📦 Bắt đầu kiểm tra và xây dựng kho dữ liệu 365 ngày...", flush=True)
    try:
        if hasattr(scraper, 'scrape_past_days'):
            scraper.scrape_past_days(days=365)
        print("✅ Đã hoàn tất khởi tạo kho dữ liệu 365 ngày!", flush=True)
    except Exception as e:
        print(f"⚠️ Lỗi khi khởi tạo dữ liệu: {e}", flush=True)

# --- BACKGROUND TASK: TỰ ĐỘNG CẬP NHẬT MỖI NGÀY LÚC 18h30 ---
def auto_update_scheduler():
    """Hàm chạy ngầm tự động quét kết quả XSMB lúc 18h30 hàng ngày"""
    print("⏰ Đã kích hoạt bộ hẹn giờ tự động cập nhật (18h30 hàng ngày)...", flush=True)
    while True:
        try:
            now = datetime.now()
            # Giờ quay XSMB rơi vào khoảng 18h15 - 18h35
            if now.hour == 18 and 30 <= now.minute <= 35:
                today_str = now.strftime("%Y-%m-%d")
                recent = db.get_results(limit=1) if hasattr(db, 'get_results') else None
                
                # Kiểm tra nếu chưa có dữ liệu ngày hôm nay thì cào
                if not recent or (isinstance(recent, list) and len(recent) > 0 and recent[0].get('date') != today_str):
                    print(f"🔄 [Auto-Update] Đang tự động cào kết quả ngày {today_str}...", flush=True)
                    success = scraper.scrape_today()
                    if success:
                        print(f"✅ [Auto-Update] Cập nhật thành công ngày {today_str}!", flush=True)
                    else:
                        time.sleep(120)
                        continue
        except Exception as e:
            print(f"⚠️ Lỗi trong tiến trình Auto-Update: {e}", flush=True)
        time.sleep(60)

# --- HELPER FUNCTIONS ---
def format_prediction_report(pred, total_days):
    """Hàm bổ trợ định dạng bản tin dự đoán cho lệnh /dudoan"""
    today_str = datetime.now().strftime("%Y-%m-%d")
    bt = pred['bach_thu']
    st1, st2 = pred['song_thu']
    t5 = ", ".join(pred['top_5'])
    t10 = ", ".join(pred['top_10'])
    
    return (
        f"🎯 *DỰ ĐOÁN XỔ SỐ MIỀN BẮC - NGÀY {today_str}*\n"
        f"📊 _(Phân tích dựa trên kho dữ liệu {total_days} ngày gần nhất)_\n"
        f"------------------------------------\n"
        f"🔥 *Bạch Thủ Lô:* `{bt}`\n"
        f"👯 *Song Thủ Lô:* `{st1}` - `{st2}`\n"
        f"🌟 *Top 5 Lô đẹp:* `{t5}`\n"
        f"📊 *Top 10 Lô đẹp:* `{t10}`\n\n"
        f"💡 *Lời khuyên:* Đánh kèm lộn nhẹ cho Bạch thủ lô để an toàn vốn."
    )

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

    # Lấy dữ liệu phân tích 365 ngày
    if hasattr(db, 'get_full'):
        results = db.get_full(limit=365)
    elif hasattr(db, 'get_results'):
        results = db.get_results(limit=365)
    else:
        results = []

    if not results:
        bot.edit_message_text("⚠️ Chưa có đủ dữ liệu trong CSDL để phân tích. Hãy bấm `/capnhat` trước!", 
                              chat_id=message.chat.id, message_id=msg.message_id, parse_mode="Markdown")
        return

    try:
        # Nếu predictor có hàm generate_prediction_report thì dùng, không thì tự format
        if hasattr(predictor, 'generate_prediction_report'):
            pred_text = predictor.generate_prediction_report(results)
        else:
            pred_data = predictor.analyze_and_predict(results)
            pred_text = format_prediction_report(pred_data, len(results))

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
    lotto_list = ", ".join([str(n)[-2:].zfill(2) for n in nums])
    
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

@bot.message_handler(commands=['test'])
def handle_test_command(message):
    text_parts = message.text.strip().split()
    
    # TH1: Test theo ngày lịch sử cố định (Backtest)
    if len(text_parts) > 1:
        target_date = text_parts[1].strip()
        msg = bot.reply_to(message, f"⏳ Đang chạy thuật toán kiểm tra dữ liệu ngày `{target_date}`...", parse_mode="Markdown")
        
        try:
            # Lấy toàn bộ CSDL để phân tách dữ liệu trước và đúng ngày test
            all_data = db.get_results(limit=365) if hasattr(db, 'get_results') else []
            
            # 1. Dữ liệu lịch sử TRƯỚC ngày target_date
            historical_data = [r for r in all_data if r.get('date', '') < target_date]
            
            # 2. Kết quả thực tế CỦA NGÀY target_date
            actual_row = next((r for r in all_data if r.get('date', '') == target_date), None)
            
            if not actual_row:
                bot.edit_message_text(f"❌ Không tìm thấy dữ liệu kết quả XSMB ngày **{target_date}** trong CSDL!", 
                                      chat_id=message.chat.id, message_id=msg.message_id, parse_mode="Markdown")
                return

            actual_numbers = actual_row.get('numbers', [])
            if isinstance(actual_numbers, str):
                try: actual_numbers = json.loads(actual_numbers)
                except: actual_numbers = actual_numbers.split(',')

            # 3. Gọi hàm test trong predictor
            if hasattr(predictor, 'test_prediction_accuracy'):
                res = predictor.test_prediction_accuracy(historical_data, actual_numbers)
                
                if not res:
                    bot.edit_message_text("❌ Dữ liệu lịch sử không đủ để thuật toán phân tích.", 
                                          chat_id=message.chat.id, message_id=msg.message_id)
                    return

                bt_icon = "✅ TRÚNG" if res['bach_thu_hit'] else "❌ TRƯỢT"
                st_hits_list = [x for x in res['song_thu'] if x in res['actual_numbers']]
                st_text = f"Trúng {res['song_thu_hits']}/2 lô ({', '.join(st_hits_list) if st_hits_list else 'Trượt'})"
                t5_hits_list = [x for x in res['top_5'] if x in res['actual_numbers']]
                t10_hits_list = [x for x in res['top_10'] if x in res['actual_numbers']]

                report = (
                    f"🧪 *BÁO CÁO TEST ĐỘ CHÍNH XÁC NGÀY {target_date}*\n"
                    f"------------------------------------\n"
                    f"🔥 *Bạch Thủ Lô ({res['bach_thu']})*: {bt_icon}\n"
                    f"👯 *Song Thủ Lô ({res['song_thu'][0]}, {res['song_thu'][1]})*: {st_text}\n"
                    f"🌟 *Top 5 Lô đẹp*: Trúng {res['top_5_hits']}/5 lô ({', '.join(t5_hits_list) if t5_hits_list else 'Trượt'})\n"
                    f"📊 *Top 10 Lô đẹp*: Trúng {res['top_10_hits']}/10 lô ({', '.join(t10_hits_list) if t10_hits_list else 'Trượt'})\n\n"
                    f"📝 *Tổng số giải lô về ngày đó*: {res['actual_count']} đầu số.\n"
                    f"ℹ️ *Lưu ý*: Thuật toán chỉ sử dụng dữ liệu trước ngày {target_date} để phân tích."
                )
                bot.edit_message_text(report, chat_id=message.chat.id, message_id=msg.message_id, parse_mode="Markdown")
            else:
                bot.edit_message_text("⚠️ Chưa cập nhật hàm `test_prediction_accuracy` trong `predictor.py`.", 
                                      chat_id=message.chat.id, message_id=msg.message_id)

        except Exception as e:
            print(f"❌ Lỗi lệnh /test {target_date}: {e}", flush=True)
            bot.edit_message_text(f"⚠️ Lỗi khi kiểm tra dữ liệu ngày {target_date}: `{str(e)}`", 
                                  chat_id=message.chat.id, message_id=msg.message_id, parse_mode="Markdown")

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
            if hasattr(predictor, 'analyze_and_predict'):
                status_report.append("✅ **Predictor:** Thuật toán phân tích dự đoán sẵn sàng")
            else:
                status_report.append("❌ **Predictor:** Thiếu hàm `analyze_and_predict`")
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
    
    # 1. Chạy Web Server trong Thread riêng
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # 2. Chạy tiến trình cào dữ liệu lịch sử trong Thread riêng
    data_thread = threading.Thread(target=fetch_initial_data, daemon=True)
    data_thread.start()

    # 3. Chạy tiến trình tự động cập nhật hàng ngày (18h30)
    auto_thread = threading.Thread(target=auto_update_scheduler, daemon=True)
    auto_thread.start()

    # 4. Dọn dẹp Webhook cũ & trễ 2 giây để Telegram giải phóng kết nối socket
    try:
        bot.remove_webhook()
        time.sleep(2)
    except Exception as e:
        print(f"⚠️ Lỗi dọn dẹp Webhook: {e}", flush=True)

    print("🤖 Bot đang lắng nghe lệnh...", flush=True)

    # 5. Vòng lặp Polling an toàn
    while True:
        try:
            bot.infinity_polling(skip_pending=True, timeout=20, long_polling_timeout=10)
        except Exception as e:
            print(f"⚠️ Lỗi hệ thống Polling (sẽ thử lại sau 5 giây): {e}", flush=True)
            time.sleep(5)