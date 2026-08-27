import os
import sys
import time
import threading
import json
import re
from datetime import datetime, timedelta, date
import telebot
from flask import Flask

# Import các module nội bộ
import database as db
import scraper
import predictor

# Lấy Token từ Environment Variables trên Render
TOKEN = os.getenv("TELEGRAM_TOKEN")

if not TOKEN:
    print("❌ LỖI FATAL: Chưa cấu hình TELEGRAM_TOKEN trong Environment Variables trên Render!", flush=True)
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

# --- HELPER KHẮC PHỤC LỖI ÉP KIỂU NGÀY ---
def normalize_date(val):
    """ Ép mọi kiểu ngày (datetime, date, str) về chuỗi YYYY-MM-DD """
    if not val:
        return ""
    if isinstance(val, (datetime, date)):
        return val.strftime("%Y-%m-%d")
    return str(val)[:10]

# --- BACKGROUND TASKS ---
def fetch_initial_data():
    print("📦 Bắt đầu kiểm tra và xây dựng kho dữ liệu 365 ngày...", flush=True)
    try:
        if hasattr(scraper, 'scrape_past_days'):
            scraper.scrape_past_days(days=365)
        print("✅ Đã hoàn tất khởi tạo kho dữ liệu 365 ngày!", flush=True)
    except Exception as e:
        print(f"⚠️ Lỗi khi khởi tạo dữ liệu: {e}", flush=True)

def auto_update_scheduler():
    print("⏰ Đã kích hoạt bộ hẹn giờ tự động cập nhật (18h30 hàng ngày)...", flush=True)
    while True:
        try:
            now = datetime.now()
            if now.hour == 18 and 30 <= now.minute <= 35:
                today_str = now.strftime("%Y-%m-%d")
                recent = db.get_results(limit=1) if hasattr(db, 'get_results') else None
                
                if not recent or (isinstance(recent, list) and len(recent) > 0 and normalize_date(recent[0].get('date')) != today_str):
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

# --- TELEGRAM BOT HANDLERS ---
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    help_text = (
        "🤖 *BOT DỰ ĐOÁN XỔ SỐ MIỀN BẮC (XSMB)*\n\n"
        "Các câu lệnh khả dụng:\n"
        "🔹 `/dudoan` - Nhận dự đoán lô đẹp cho ngày hôm nay\n"
        "🔹 `/dudoandb` - Dự đoán dàn 10, 20, 36 số Giải Đặc Biệt ngày tiếp theo\n"
        "🔹 `/ketqua` - Xem kết quả XSMB mới nhất có trong CSDL\n"
        "🔹 `/capnhat` - Ép bot quét cập nhật kết quả hôm nay ngay lập tức\n"
        "🔹 `/thongke` hoặc `/stats` - Trạng thái kho dữ liệu hiện tại\n"
        "🔹 `/test YYYY-MM-DD` - Backtest tỷ lệ trúng LÔ ngày cố định\n"
        "🔹 `/testdb YYYY-MM-DD` - Backtest GIẢI ĐẶC BIỆT ngày cố định\n"
        "🔹 `/testdb YYYY-MM-DD => DD` - Backtest GIẢI ĐẶC BIỆT theo khoảng ngày\n"
        "🔹 `/help` - Xem lại hướng dẫn này"
    )
    bot.reply_to(message, help_text, parse_mode="Markdown")

@bot.message_handler(commands=['testdb'])
def handle_test_db_command(message):
    raw_text = message.text.strip()
    text_parts = raw_text.split()
    
    if len(text_parts) <= 1:
        bot.reply_to(
            message, 
            "⚠️ Vui lòng nhập ngày theo cú pháp:\n"
            "▫️ Lẻ 1 ngày: `/testdb 2026-08-19`\n"
            "▫️ Theo dải ngày: `/testdb 2026-08-01 => 25`", 
            parse_mode="Markdown"
        )
        return

    raw_input = " ".join(text_parts[1:]).strip()
    dates_to_test = []

    # Bắt cú pháp dải ngày (Hỗ trợ =>, ->, -, hoặc dấu cách)
    range_match = re.search(r'(\d{4}-\d{2}-\d{2})\s*(?:=>|->|-|\s+)\s*(\d{1,2}|\d{4}-\d{2}-\d{2})$', raw_input)
    
    if range_match:
        start_str, end_val_str = range_match.group(1), range_match.group(2)
        try:
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
        except Exception as e:
            bot.reply_to(message, f"❌ Lỗi định dạng khoảng ngày: `{e}`", parse_mode="Markdown")
            return

    elif re.match(r'^\d{4}-\d{2}-\d{2}$', text_parts[1]):
        dates_to_test.append(text_parts[1])
    else:
        bot.reply_to(message, "❌ Định dạng tham số không hợp lệ.", parse_mode="Markdown")
        return

    # XỬ LÝ TEST DẢI NGÀY
    if len(dates_to_test) > 1:
        msg = bot.reply_to(message, f"⏳ Đang kiểm tra {len(dates_to_test)} ngày (từ `{dates_to_test[0]}` đến `{dates_to_test[-1]}`)...", parse_mode="Markdown")
        
        try:
            all_data = db.get_results(limit=500) if hasattr(db, 'get_results') else []
            hit_10_cnt = hit_20_cnt = hit_36_cnt = 0
            valid_days_cnt = 0
            details_list = []

            for target_date in dates_to_test:
                # Ép kiểu dữ liệu ngày chuẩn hóa hoàn toàn trước khi so sánh
                historical_data = [r for r in all_data if normalize_date(r.get('date')) < target_date]
                actual_row = next((r for r in all_data if normalize_date(r.get('date')) == target_date), None)

                if not actual_row:
                    details_list.append(f"📅 **{target_date}**: ⚠️ _Thiếu dữ liệu_")
                    continue

                actual_numbers = actual_row.get('numbers', [])
                if isinstance(actual_numbers, str):
                    try: actual_numbers = json.loads(actual_numbers)
                    except: actual_numbers = actual_numbers.split(',')

                if hasattr(predictor, 'test_db_accuracy'):
                    res = predictor.test_db_accuracy(historical_data, actual_numbers)
                    if not res: continue

                    valid_days_cnt += 1
                    actual_db = res['actual_db']

                    is_h10 = res.get('is_hit_10', res.get('is_hit', False))
                    is_h20 = res.get('is_hit_20', False)
                    is_h36 = res.get('is_hit_36', False)

                    if is_h10: hit_10_cnt += 1
                    if is_h20: hit_20_cnt += 1
                    if is_h36: hit_36_cnt += 1

                    h10_icon = "✅" if is_h10 else "❌"
                    h20_icon = "✅" if is_h20 else "❌"
                    h36_icon = "✅" if is_h36 else "❌"

                    details_list.append(
                        f"📅 **{target_date}** (Đề: **{actual_db}**)\n"
                        f"└ Dàn 10: {h10_icon} | Dàn 20: {h20_icon} | Dàn 36: {h36_icon}"
                    )

            if valid_days_cnt == 0:
                bot.edit_message_text("❌ Chưa tìm thấy dữ liệu phù hợp trong dải ngày này.", chat_id=message.chat.id, message_id=msg.message_id)
                return

            rate_10 = (hit_10_cnt / valid_days_cnt) * 100
            rate_20 = (hit_20_cnt / valid_days_cnt) * 100
            rate_36 = (hit_36_cnt / valid_days_cnt) * 100

            report = (
                f"👑 *BÁO CÁO TEST GIẢI ĐẶC BIỆT THEO KHOẢNG NGÀY*\n"
                f"🗓 **Giai đoạn:** `{dates_to_test[0]}` ➔ `{dates_to_test[-1]}` ({valid_days_cnt} ngày)\n"
                f"------------------------------------\n"
                + "\n".join(details_list) +
                f"\n------------------------------------\n"
                f"📊 **TỔNG KẾT TỶ LỆ TRÚNG:**\n"
                f"🎯 **Dàn 10 số:** `{hit_10_cnt}/{valid_days_cnt}` ngày (**{rate_10:.1f}%**)\n"
                f"🎯 **Dàn 20 số:** `{hit_20_cnt}/{valid_days_cnt}` ngày (**{rate_20:.1f}%**)\n"
                f"🎯 **Dàn 36 số:** `{hit_36_cnt}/{valid_days_cnt}` ngày (**{rate_36:.1f}%**)\n"
            )
            bot.edit_message_text(report, chat_id=message.chat.id, message_id=msg.message_id, parse_mode="Markdown")

        except Exception as e:
            bot.edit_message_text(f"⚠️ Lỗi khi kiểm tra dải ngày: `{str(e)}`", chat_id=message.chat.id, message_id=msg.message_id, parse_mode="Markdown")

    # XỬ LÝ TEST 1 NGÀY ĐƠN LẺ
    else:
        target_date = dates_to_test[0]
        msg = bot.reply_to(message, f"⏳ Đang kiểm tra Giải Đặc Biệt ngày `{target_date}`...", parse_mode="Markdown")

        try:
            all_data = db.get_results(limit=500) if hasattr(db, 'get_results') else []
            historical_data = [r for r in all_data if normalize_date(r.get('date')) < target_date]
            actual_row = next((r for r in all_data if normalize_date(r.get('date')) == target_date), None)

            if not actual_row:
                bot.edit_message_text(f"❌ Không tìm thấy dữ liệu XSMB ngày **{target_date}** trong CSDL!", chat_id=message.chat.id, message_id=msg.message_id, parse_mode="Markdown")
                return

            actual_numbers = actual_row.get('numbers', [])
            if isinstance(actual_numbers, str):
                try: actual_numbers = json.loads(actual_numbers)
                except: actual_numbers = actual_numbers.split(',')

            if hasattr(predictor, 'test_db_accuracy'):
                res = predictor.test_db_accuracy(historical_data, actual_numbers)
                if not res:
                    bot.edit_message_text("❌ Không đủ dữ liệu lịch sử để phân tích.", chat_id=message.chat.id, message_id=msg.message_id)
                    return

                status_10 = "✅ TRÚNG" if res.get('is_hit_10', res.get('is_hit', False)) else "❌ TRƯỢT"
                status_20 = "✅ TRÚNG" if res.get('is_hit_20', False) else "❌ TRƯỢT"
                status_36 = "✅ TRÚNG" if res.get('is_hit_36', False) else "❌ TRƯỢT"

                report = (
                    f"👑 *BÁO CÁO TEST GIẢI ĐẶC BIỆT NGÀY {target_date}*\n"
                    f"------------------------------------\n"
                    f"🎯 *Dàn 10 số:* {', '.join(res.get('predicted_10', []))}\n"
                    f"📌 *Trạng thái:* {status_10}\n\n"
                    f"🎯 *Dàn 20 số:* {', '.join(res.get('predicted_20', []))}\n"
                    f"📌 *Trạng thái:* {status_20}\n\n"
                    f"🎯 *Dàn 36 số:* {', '.join(res.get('predicted_36', []))}\n"
                    f"📌 *Trạng thái:* {status_36}\n\n"
                    f"🎰 *Kết quả ĐB thực tế:* {res['actual_db']}\n"
                    f"------------------------------------"
                )
                bot.edit_message_text(report, chat_id=message.chat.id, message_id=msg.message_id, parse_mode="Markdown")

        except Exception as e:
            bot.edit_message_text(f"⚠️ Lỗi khi kiểm tra ĐB ngày {target_date}: `{str(e)}`", chat_id=message.chat.id, message_id=msg.message_id, parse_mode="Markdown")

@bot.message_handler(commands=['thongke', 'stats'])
def handle_stats(message):
    count = db.count_results() if hasattr(db, 'count_results') else 0
    min_date, max_date = db.get_date_range() if hasattr(db, 'get_date_range') else (None, None)
    
    stats_msg = (
        "📈 *THỐNG KÊ KHO DỮ LIỆU CSDL*\n\n"
        f"▫️ **Tổng số ngày đã lưu:** `{count}` ngày\n"
        f"▫️ **Ngày dữ liệu cũ nhất:** `{normalize_date(min_date)}`\n"
        f"▫️ **Ngày dữ liệu mới nhất:** `{normalize_date(max_date)}`"
    )
    bot.reply_to(message, stats_msg, parse_mode="Markdown")

# --- LUỒNG CHÍNH ---
if __name__ == '__main__':
    print("🚀 Khởi động Flask & Bot Telegram...", flush=True)
    
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    data_thread = threading.Thread(target=fetch_initial_data, daemon=True)
    data_thread.start()

    auto_thread = threading.Thread(target=auto_update_scheduler, daemon=True)
    auto_thread.start()

    try:
        bot.remove_webhook()
        time.sleep(2)
    except Exception as e:
        print(f"⚠️ Lỗi dọn dẹp Webhook: {e}", flush=True)

    print("🤖 Bot đang lắng nghe lệnh...", flush=True)

    while True:
        try:
            bot.infinity_polling(skip_pending=True, timeout=20, long_polling_timeout=10)
        except Exception as e:
            print(f"⚠️ Lỗi hệ thống Polling (thử lại sau 5 giây): {e}", flush=True)
            time.sleep(5)