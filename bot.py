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

# --- HELPER CHUẨN HÓA DỮ LIỆU ---
def normalize_date(val):
    if not val:
        return ""
    if isinstance(val, (datetime, date)):
        return val.strftime("%Y-%m-%d")
    return str(val)[:10]

def parse_date_range(raw_input):
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
        "🔹 `/dudoan` - Nhận dự đoán Bach thủ, Xiên 2, Xiên 3, Xiên 4 hôm nay\n"
        "🔹 `/dudoandb` - Dự đoán dàn 10, 20, 36 số Giải Đặc Biệt kỳ tiếp theo\n"
        "🔹 `/ketqua` - Xem kết quả XSMB mới nhất có trong CSDL\n"
        "🔹 `/capnhat` - Ép bot quét cập nhật kết quả hôm nay ngay lập tức\n"
        "🔹 `/thongke` hoặc `/stats` - Trạng thái kho dữ liệu hiện tại\n"
        "🔹 `/test YYYY-MM-DD` - Backtest LÔ & XIÊN ngày cố định\n"
        "🔹 `/test YYYY-MM-DD => DD` - Backtest LÔ & XIÊN theo dải ngày\n"
        "🔹 `/testdb YYYY-MM-DD` - Backtest ĐỀ ngày cố định\n"
        "🔹 `/testdb YYYY-MM-DD => DD` - Backtest ĐỀ theo dải ngày\n"
        "🔹 `/help` - Xem lại hướng dẫn này"
    )
    bot.reply_to(message, help_text, parse_mode="Markdown")

@bot.message_handler(commands=['dudoan'])
def handle_prediction(message):
    msg = bot.reply_to(message, "⏳ Đang phân tích ma trận 100 kỳ gần nhất...")
    today_str = datetime.now().strftime("%Y-%m-%d")
    recent = db.get_results(limit=1) if hasattr(db, 'get_results') else None
    
    if not recent or (isinstance(recent, list) and len(recent) > 0 and normalize_date(recent[0].get('date')) != today_str):
        scraper.scrape_today()

    results = db.get_results(limit=100) if hasattr(db, 'get_results') else []

    if not results:
        bot.edit_message_text("⚠️ Chưa có đủ dữ liệu trong CSDL để phân tích.", chat_id=message.chat.id, message_id=msg.message_id)
        return

    try:
        pred_data = predictor.analyze_and_predict(results)
        bt = pred_data.get('bach_thu', '--')
        
        # Định dạng danh sách Xiên
        str_x2 = "\n".join([f"  • Cặp {i+1}: `{pair[0]}` - `{pair[1]}`" for i, pair in enumerate(pred_data.get('xien_2', []))])
        str_x3 = " - ".join([f"`{num}`" for num in pred_data.get('xien_3', [])])
        str_x4 = " - ".join([f"`{num}`" for num in pred_data.get('xien_4', [])])

        report = (
            f"🎯 *DỰ ĐOÁN XỔ SỐ MIỀN BẮC - NGÀY {today_str}*\n"
            f"📊 _(Phân tích nhịp rơi & phong độ 100 kỳ gần nhất)_\n"
            f"------------------------------------\n"
            f"🔥 *Bạch Thủ Lô:* `{bt}`\n\n"
            f"👯 *Xiên 2 (Các cặp tiềm năng):*\n{str_x2}\n\n"
            f"🥉 *Xiên 3:* {str_x3}\n"
            f"🏅 *Xiên 4:* {str_x4}\n"
            f"------------------------------------\n"
            f"💡 *Lời khuyên:* Đánh kèm lộn nhẹ cho Bạch thủ lô để bảo toàn vốn."
        )
        bot.edit_message_text(report, chat_id=message.chat.id, message_id=msg.message_id, parse_mode="Markdown")
    except Exception as e:
        bot.edit_message_text(f"⚠️ Lỗi khi tạo dự đoán: {e}", chat_id=message.chat.id, message_id=msg.message_id)

@bot.message_handler(commands=['dudoandb'])
def handle_prediction_db(message):
    msg = bot.reply_to(message, "👑 Đang phân tích ma trận ĐB 30 kỳ gần nhất...")
    results = db.get_results(limit=100) if hasattr(db, 'get_results') else []

    if not results:
        bot.edit_message_text("⚠️ Chưa có đủ dữ liệu trong CSDL để phân tích.", chat_id=message.chat.id, message_id=msg.message_id)
        return

    try:
        pred_db = predictor.analyze_and_predict_db(results)
        list_10 = ", ".join(pred_db.get('top_10_db', []))
        list_20 = ", ".join(pred_db.get('top_20_db', []))
        list_36 = ", ".join(pred_db.get('top_36_db', []))

        report = (
            f"🔮 *DỰ ĐOÁN GIẢI ĐẶC BIỆT (ĐỀ ĐUÔI) - KỲ TỚI*\n"
            f"📊 _(Phân tích Chạm Hot & Tổng Đề nâng cao)_\n"
            f"------------------------------------\n"
            f"🎯 *Dàn 10 số (Trọng tâm):*\n`{list_10}`\n\n"
            f"🎯 *Dàn 20 số (Tối ưu):*\n`{list_20}`\n\n"
            f"🎯 *Dàn 36 số (Bao phủ):*\n`{list_36}`\n\n"
            f"💡 *Gợi ý:* Khuyên dùng dàn 20 hoặc 36 số để nuôi khung 2-3 ngày."
        )
        bot.edit_message_text(report, chat_id=message.chat.id, message_id=msg.message_id, parse_mode="Markdown")
    except Exception as e:
        bot.edit_message_text(f"⚠️ Lỗi khi phân tích Giải Đặc Biệt: {e}", chat_id=message.chat.id, message_id=msg.message_id)

@bot.message_handler(commands=['test'])
def handle_test_command(message):
    raw_text = message.text.strip()
    text_parts = raw_text.split()
    
    if len(text_parts) <= 1:
        count = db.count_results() if hasattr(db, 'count_results') else 0
        bot.reply_to(message, f"🧪 **Hệ thống sẵn sàng!** CSDL đang lưu `{count}` ngày.", parse_mode="Markdown")
        return

    raw_input = " ".join(text_parts[1:]).strip()
    dates_to_test = parse_date_range(raw_input)

    if not dates_to_test:
        bot.reply_to(message, "❌ Định dạng không hợp lệ. Ví dụ: `/test 2026-08-01 => 25`", parse_mode="Markdown")
        return

    if len(dates_to_test) > 1:
        msg = bot.reply_to(message, f"⏳ Đang test LÔ & XIÊN {len(dates_to_test)} ngày...", parse_mode="Markdown")
        try:
            all_data = db.get_results(limit=500) if hasattr(db, 'get_results') else []
            valid_cnt = bt_hits = x2_total = x3_hits = x4_hits = 0
            details_list = []

            for target_date in dates_to_test:
                historical_data = [r for r in all_data if normalize_date(r.get('date')) < target_date][:100]
                actual_row = next((r for r in all_data if normalize_date(r.get('date')) == target_date), None)

                if not actual_row: continue

                actual_numbers = actual_row.get('numbers', [])
                res = predictor.test_prediction_accuracy(historical_data, actual_numbers)
                if not res: continue

                valid_cnt += 1
                if res.get('bach_thu_hit'): bt_hits += 1
                
                x2_cnt = res.get('xien_2_hits_count', 0)
                x2_total += x2_cnt
                
                if res.get('xien_3_hit'): x3_hits += 1
                if res.get('xien_4_hit'): x4_hits += 1

                bt_icon = "✅" if res.get('bach_thu_hit') else "❌"
                x3_icon = "✅" if res.get('xien_3_hit') else "❌"
                x4_icon = "✅" if res.get('xien_4_hit') else "❌"

                details_list.append(
                    f"📅 **{target_date}**: BT {bt_icon} (`{res.get('bach_thu')}`) | "
                    f"X2: **{x2_cnt}/2** | X3: {x3_icon} | X4: {x4_icon}"
                )

            if valid_cnt == 0:
                bot.edit_message_text("❌ Không có dữ liệu phù hợp.", chat_id=message.chat.id, message_id=msg.message_id)
                return

            bt_rate = (bt_hits / valid_cnt) * 100
            report_header = f"🧪 *BÁO CÁO TEST LÔ & XIÊN ({valid_cnt} NGÀY)*\n------------------------------------\n"
            report_footer = (
                f"\n------------------------------------\n"
                f"📊 **TỔNG KẾT TỶ LỆ TRÚNG:**\n"
                f"🔥 **Bạch Thủ Lô:** Trúng `{bt_hits}/{valid_cnt}` ngày (**{bt_rate:.1f}%**)\n"
                f"👯 **Xiên 2:** Trúng tổng cộng **{x2_total}** cặp\n"
                f"🥉 **Xiên 3:** Trúng **{x3_hits}/{valid_cnt}** ngày\n"
                f"🏅 **Xiên 4:** Trúng **{x4_hits}/{valid_cnt}** ngày\n"
            )

            full_report = report_header + "\n".join(details_list) + report_footer
            if len(full_report) > 4000:
                full_report = report_header + "\n".join(details_list[:15]) + f"\n... (ẩn {len(details_list)-15} ngày) ..." + report_footer

            bot.edit_message_text(full_report, chat_id=message.chat.id, message_id=msg.message_id, parse_mode="Markdown")

        except Exception as e:
            bot.edit_message_text(f"⚠️ Lỗi test: `{str(e)}`", chat_id=message.chat.id, message_id=msg.message_id, parse_mode="Markdown")
    else:
        target_date = dates_to_test[0]
        msg = bot.reply_to(message, f"⏳ Đang test LÔ & XIÊN ngày `{target_date}`...", parse_mode="Markdown")
        try:
            all_data = db.get_results(limit=500) if hasattr(db, 'get_results') else []
            historical_data = [r for r in all_data if normalize_date(r.get('date')) < target_date][:100]
            actual_row = next((r for r in all_data if normalize_date(r.get('date')) == target_date), None)

            if not actual_row:
                bot.edit_message_text(f"❌ Thiếu dữ liệu ngày {target_date}.", chat_id=message.chat.id, message_id=msg.message_id)
                return

            res = predictor.test_prediction_accuracy(historical_data, actual_row.get('numbers', []))
            bt_icon = "✅ TRÚNG" if res.get('bach_thu_hit') else "❌ TRƯỢT"
            x3_icon = "✅ TRÚNG" if res.get('xien_3_hit') else "❌ TRƯỢT"
            x4_icon = "✅ TRÚNG" if res.get('xien_4_hit') else "❌ TRƯỢT"

            report = (
                f"🧪 *BÁO CÁO TEST LÔ & XIÊN NGÀY {target_date}*\n"
                f"------------------------------------\n"
                f"🔥 *Bạch Thủ Lô ({res.get('bach_thu')})*: {bt_icon}\n"
                f"👯 *Xiên 2*: Trúng {res.get('xien_2_hits_count', 0)}/2 cặp\n"
                f"🥉 *Xiên 3 ({', '.join(res.get('xien_3', []))})*: {x3_icon}\n"
                f"🏅 *Xiên 4 ({', '.join(res.get('xien_4', []))})*: {x4_icon}\n"
            )
            bot.edit_message_text(report, chat_id=message.chat.id, message_id=msg.message_id, parse_mode="Markdown")
        except Exception as e:
            bot.edit_message_text(f"⚠️ Lỗi: `{str(e)}`", chat_id=message.chat.id, message_id=msg.message_id, parse_mode="Markdown")

@bot.message_handler(commands=['testdb'])
def handle_test_db_command(message):
    raw_text = message.text.strip()
    text_parts = raw_text.split()
    
    if len(text_parts) <= 1:
        bot.reply_to(message, "⚠️ Cú pháp: `/testdb 2026-08-01 => 25`", parse_mode="Markdown")
        return

    raw_input = " ".join(text_parts[1:]).strip()
    dates_to_test = parse_date_range(raw_input)

    if len(dates_to_test) > 1:
        msg = bot.reply_to(message, f"⏳ Đang test ĐỀ {len(dates_to_test)} ngày...", parse_mode="Markdown")
        try:
            all_data = db.get_results(limit=500) if hasattr(db, 'get_results') else []
            h10 = h20 = h36 = valid_cnt = 0
            details_list = []

            for target_date in dates_to_test:
                historical_data = [r for r in all_data if normalize_date(r.get('date')) < target_date][:100]
                actual_row = next((r for r in all_data if normalize_date(r.get('date')) == target_date), None)

                if not actual_row: continue

                res = predictor.test_db_accuracy(historical_data, actual_row.get('numbers', []))
                if not res: continue

                valid_cnt += 1
                if res['is_hit_10']: h10 += 1
                if res['is_hit_20']: h20 += 1
                if res['is_hit_36']: h36 += 1

                details_list.append(
                    f"📅 **{target_date}** (Đề: **{res['actual_db']}**)\n"
                    f"└ Dàn 10: {'✅' if res['is_hit_10'] else '❌'} | Dàn 20: {'✅' if res['is_hit_20'] else '❌'} | Dàn 36: {'✅' if res['is_hit_36'] else '❌'}"
                )

            if valid_cnt == 0:
                bot.edit_message_text("❌ Không tìm thấy dữ liệu.", chat_id=message.chat.id, message_id=msg.message_id)
                return

            report_header = f"👑 *BÁO CÁO TEST GIẢI ĐẶC BIỆT ({valid_cnt} NGÀY)*\n------------------------------------\n"
            report_footer = (
                f"\n------------------------------------\n"
                f"📊 **TỔNG KẾT TỶ LỆ TRÚNG:**\n"
                f"🎯 **Dàn 10 số:** `{h10}/{valid_cnt}` ngày (**{(h10/valid_cnt)*100:.1f}%**)\n"
                f"🎯 **Dàn 20 số:** `{h20}/{valid_cnt}` ngày (**{(h20/valid_cnt)*100:.1f}%**)\n"
                f"🎯 **Dàn 36 số:** `{h36}/{valid_cnt}` ngày (**{(h36/valid_cnt)*100:.1f}%**)\n"
            )

            full_report = report_header + "\n".join(details_list) + report_footer
            if len(full_report) > 4000:
                full_report = report_header + "\n".join(details_list[:15]) + f"\n... (ẩn {len(details_list)-15} ngày) ..." + report_footer

            bot.edit_message_text(full_report, chat_id=message.chat.id, message_id=msg.message_id, parse_mode="Markdown")
        except Exception as e:
            bot.edit_message_text(f"⚠️ Lỗi test Đề: `{str(e)}`", chat_id=message.chat.id, message_id=msg.message_id, parse_mode="Markdown")

@bot.message_handler(commands=['ketqua'])
def handle_latest_result(message):
    results = db.get_results(limit=1) if hasattr(db, 'get_results') else None
    if not results:
        bot.reply_to(message, "⚠️ Chưa có dữ liệu trong CSDL.")
        return
    
    latest = results[0]
    date_str = normalize_date(latest.get('date'))
    
    if hasattr(predictor, 'parse_numbers'):
        nums = predictor.parse_numbers(latest)
    else:
        nums = latest.get('numbers', [])
    
    db_val = nums[0] if len(nums) > 0 else "---"
    g1_val = nums[1] if len(nums) > 1 else "---"
    lotto_list = ", ".join(nums)
    
    res_msg = (
        f"📊 *KẾT QUẢ XSMB NGÀY {date_str}*\n\n"
        f"🏆 **Giải Đặc Biệt:** `{db_val}`\n"
        f"🥇 **Giải Nhất:** `{g1_val}`\n"
        f"🎲 **Lô tô về ({len(nums)} giải):**\n`{lotto_list}`"
    )
    bot.reply_to(message, res_msg, parse_mode="Markdown")

@bot.message_handler(commands=['capnhat'])
def handle_manual_update(message):
    msg = bot.reply_to(message, "🔍 Đang cào kết quả mới...")
    if scraper.scrape_today():
        bot.edit_message_text("✅ Cập nhật thành công!", chat_id=message.chat.id, message_id=msg.message_id)
    else:
        bot.edit_message_text("⚠️ Chưa có kết quả mới.", chat_id=message.chat.id, message_id=msg.message_id)

@bot.message_handler(commands=['thongke', 'stats'])
def handle_stats(message):
    count = db.count_results() if hasattr(db, 'count_results') else 0
    min_d, max_d = db.get_date_range() if hasattr(db, 'get_date_range') else (None, None)
    
    stats_msg = (
        "📈 *THỐNG KÊ CSDL*\n\n"
        f"▫️ **Tổng số ngày:** `{count}` ngày\n"
        f"▫️ **Từ ngày:** `{normalize_date(min_d)}` ➔ `{normalize_date(max_d)}`"
    )
    bot.reply_to(message, stats_msg, parse_mode="Markdown")

# --- LUỒNG CHÍNH ---
if __name__ == '__main__':
    print("🚀 Khởi động Flask & Bot Telegram...", flush=True)
    
    threading.Thread(target=run_flask, daemon=True).start()
    threading.Thread(target=fetch_initial_data, daemon=True).start()
    threading.Thread(target=auto_update_scheduler, daemon=True).start()

    try:
        bot.remove_webhook()
        time.sleep(2)
    except Exception as e:
        print(f"⚠️ Webhook warning: {e}", flush=True)

    print("🤖 Bot đang lắng nghe...", flush=True)

    while True:
        try:
            bot.infinity_polling(skip_pending=True, timeout=20, long_polling_timeout=10)
        except Exception as e:
            print(f"⚠️ Polling retry: {e}", flush=True)
            time.sleep(5)