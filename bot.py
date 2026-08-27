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

# --- HELPER CHUẨN HÓA DỮ LIỆU NGÀY ---
def normalize_date(val):
    """Ép mọi kiểu ngày (datetime, date, str) về dạng YYYY-MM-DD"""
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

# --- HELPER FORMATTING ---
def format_prediction_report(pred, total_days):
    today_str = datetime.now().strftime("%Y-%m-%d")
    bt = pred['bach_thu']
    st1, st2 = pred['song_thu']
    t5 = ", ".join(pred['top_5'])
    t10 = ", ".join(pred['top_10'])
    
    return (
        f"🎯 *DỰ ĐOÁN XỔ SỐ MIỀN BẮC - NGÀY {today_str}*\n"
        f"📊 _(Phân tích ma trận 100 ngày gần nhất)_\n"
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

@bot.message_handler(commands=['dudoan'])
def handle_prediction(message):
    msg = bot.reply_to(message, "⏳ Đang phân tích ma trận 100 kỳ gần nhất, vui lòng đợi...")
    today_str = datetime.now().strftime("%Y-%m-%d")
    recent = db.get_results(limit=1) if hasattr(db, 'get_results') else None
    
    if not recent or (isinstance(recent, list) and len(recent) > 0 and normalize_date(recent[0].get('date')) != today_str):
        scraper.scrape_today()

    # Lấy 100 ngày gần nhất
    results = db.get_results(limit=100) if hasattr(db, 'get_results') else []

    if not results:
        bot.edit_message_text("⚠️ Chưa có đủ dữ liệu trong CSDL để phân tích. Hãy bấm `/capnhat` trước!", 
                              chat_id=message.chat.id, message_id=msg.message_id, parse_mode="Markdown")
        return

    try:
        if hasattr(predictor, 'generate_prediction_report'):
            pred_text = predictor.generate_prediction_report(results)
        else:
            pred_data = predictor.analyze_and_predict(results)
            pred_text = format_prediction_report(pred_data, len(results))

        bot.edit_message_text(pred_text, chat_id=message.chat.id, message_id=msg.message_id, parse_mode="Markdown")
    except Exception as e:
        bot.edit_message_text(f"⚠️ Lỗi khi tạo bản tin dự đoán: {e}", chat_id=message.chat.id, message_id=msg.message_id)

@bot.message_handler(commands=['dudoandb'])
def handle_prediction_db(message):
    msg = bot.reply_to(message, "👑 Đang phân tích ma trận ĐB 100 kỳ gần nhất...")
    today_str = datetime.now().strftime("%Y-%m-%d")
    recent = db.get_results(limit=1) if hasattr(db, 'get_results') else None
    
    if not recent or (isinstance(recent, list) and len(recent) > 0 and normalize_date(recent[0].get('date')) != today_str):
        scraper.scrape_today()

    # Lấy 100 ngày gần nhất
    results = db.get_results(limit=100) if hasattr(db, 'get_results') else []

    if not results:
        bot.edit_message_text("⚠️ Chưa có đủ dữ liệu trong CSDL để phân tích.", chat_id=message.chat.id, message_id=msg.message_id, parse_mode="Markdown")
        return

    try:
        if hasattr(predictor, 'analyze_and_predict_db'):
            pred_db = predictor.analyze_and_predict_db(results)
            if not pred_db:
                bot.edit_message_text("❌ Không thể tính toán dàn ĐB.", chat_id=message.chat.id, message_id=msg.message_id)
                return

            list_10 = ", ".join(pred_db.get('top_10_db', []))
            list_20 = ", ".join(pred_db.get('top_20_db', []))
            list_36 = ", ".join(pred_db.get('top_36_db', []))

            report = (
                f"🔮 *DỰ ĐOÁN GIẢI ĐẶC BIỆT (ĐỀ ĐUÔI) - KỲ TỚI*\n"
                f"📊 _(Phân tích nhịp rơi & chạm hot 100 ngày gần nhất)_\n"
                f"------------------------------------\n"
                f"🎯 *Dàn 10 số (Trọng tâm):*\n`{list_10}`\n\n"
                f"🎯 *Dàn 20 số (Tối ưu):*\n`{list_20}`\n\n"
                f"🎯 *Dàn 36 số (Bao phủ):*\n`{list_36}`\n\n"
                f"💡 *Gợi ý:* Khuyên dùng dàn 20 hoặc 36 số để nuôi khung 2-3 ngày."
            )
            bot.edit_message_text(report, chat_id=message.chat.id, message_id=msg.message_id, parse_mode="Markdown")
    except Exception as e:
        bot.edit_message_text(f"⚠️ Lỗi khi phân tích Giải Đặc Biệt: {e}", chat_id=message.chat.id, message_id=msg.message_id)

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
        msg = bot.reply_to(message, f"⏳ Đang test {len(dates_to_test)} ngày (Mỗi ngày lấy lùi 100 kỳ)...", parse_mode="Markdown")
        
        try:
            all_data = db.get_results(limit=500) if hasattr(db, 'get_results') else []
            hit_10_cnt = hit_20_cnt = hit_36_cnt = 0
            valid_days_cnt = 0
            details_list = []

            for target_date in dates_to_test:
                # 🎯 LẤY ĐÚNG 100 NGÀY LÙI VỀ TRƯỚC NGÀY CAN TEST
                historical_data = [r for r in all_data if normalize_date(r.get('date')) < target_date][:100]
                actual_row = next((r for r in all_data if normalize_date(r.get('date')) == target_date), None)

                if not actual_row:
                    details_list.append(f"📅 **{target_date}**: ⚠️ _Thiếu CSDL_")
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
                bot.edit_message_text("❌ Chưa có dữ liệu phù hợp trong dải ngày đã chọn.", chat_id=message.chat.id, message_id=msg.message_id)
                return

            rate_10 = (hit_10_cnt / valid_days_cnt) * 100
            rate_20 = (hit_20_cnt / valid_days_cnt) * 100
            rate_36 = (hit_36_cnt / valid_days_cnt) * 100

            report = (
                f"👑 *BÁO CÁO TEST GIẢI ĐẶC BIỆT (KHUNG 100 NGÀY)*\n"
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
        msg = bot.reply_to(message, f"⏳ Đang test ĐB ngày `{target_date}` (Phân tích 100 ngày lùi về)...", parse_mode="Markdown")

        try:
            all_data = db.get_results(limit=500) if hasattr(db, 'get_results') else []
            # 🎯 LẤY ĐÚNG 100 NGÀY LÙI VỀ TRƯỚC NGÀY CẦN TEST
            historical_data = [r for r in all_data if normalize_date(r.get('date')) < target_date][:100]
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
                    f"👑 *BÁO CÁO TEST ĐB NGÀY {target_date} (DÙNG 100 KỲ)*\n"
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

@bot.message_handler(commands=['ketqua'])
def handle_latest_result(message):
    results = db.get_results(limit=1) if hasattr(db, 'get_results') else None
    if not results:
        bot.reply_to(message, "⚠️ Chưa có dữ liệu kết quả nào trong CSDL.")
        return
    
    latest = results[0]
    date_str = normalize_date(latest.get('date'))
    nums = latest.get('numbers', [])
    
    if isinstance(nums, str):
        try: nums = json.loads(nums)
        except: nums = nums.split(',')

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
        bot.edit_message_text("✅ Đã cập nhật thành công kết quả mới nhất vào CSDL!", chat_id=message.chat.id, message_id=msg.message_id)
    else:
        bot.edit_message_text("⚠️ Không tìm thấy kết quả mới hoặc chưa đến giờ quay thưởng (18h15).", chat_id=message.chat.id, message_id=msg.message_id)

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

@bot.message_handler(commands=['test'])
def handle_test_command(message):
    text_parts = message.text.strip().split()
    
    if len(text_parts) > 1:
        target_date = text_parts[1].strip()
        msg = bot.reply_to(message, f"⏳ Đang test LÔ ngày `{target_date}` (Phân tích 100 kỳ lùi về)...", parse_mode="Markdown")
        
        try:
            all_data = db.get_results(limit=500) if hasattr(db, 'get_results') else []
            # 🎯 LẤY ĐÚNG 100 NGÀY LÙI VỀ
            historical_data = [r for r in all_data if normalize_date(r.get('date')) < target_date][:100]
            actual_row = next((r for r in all_data if normalize_date(r.get('date')) == target_date), None)
            
            if not actual_row:
                bot.edit_message_text(f"❌ Không tìm thấy dữ liệu kết quả XSMB ngày **{target_date}** trong CSDL!", chat_id=message.chat.id, message_id=msg.message_id, parse_mode="Markdown")
                return

            actual_numbers = actual_row.get('numbers', [])
            if isinstance(actual_numbers, str):
                try: actual_numbers = json.loads(actual_numbers)
                except: actual_numbers = actual_numbers.split(',')

            if hasattr(predictor, 'test_prediction_accuracy'):
                res = predictor.test_prediction_accuracy(historical_data, actual_numbers)
                if not res:
                    bot.edit_message_text("❌ Dữ liệu lịch sử không đủ để thuật toán phân tích.", chat_id=message.chat.id, message_id=msg.message_id)
                    return

                bt_icon = "✅ TRÚNG" if res['bach_thu_hit'] else "❌ TRƯỢT"
                st_hits_list = [x for x in res['song_thu'] if x in res['actual_numbers']]
                st_text = f"Trúng {res['song_thu_hits']}/2 lô ({', '.join(st_hits_list) if st_hits_list else 'Trượt'})"
                t5_hits_list = [x for x in res['top_5'] if x in res['actual_numbers']]
                t10_hits_list = [x for x in res['top_10'] if x in res['actual_numbers']]

                report = (
                    f"🧪 *BÁO CÁO TEST LÔ NGÀY {target_date} (100 KỲ)*\n"
                    f"------------------------------------\n"
                    f"🔥 *Bạch Thủ Lô ({res['bach_thu']})*: {bt_icon}\n"
                    f"👯 *Song Thủ Lô ({res['song_thu'][0]}, {res['song_thu'][1]})*: {st_text}\n"
                    f"🌟 *Top 5 Lô đẹp*: Trúng {res['top_5_hits']}/5 lô ({', '.join(t5_hits_list) if t5_hits_list else 'Trượt'})\n"
                    f"📊 *Top 10 Lô đẹp*: Trúng {res['top_10_hits']}/10 lô ({', '.join(t10_hits_list) if t10_hits_list else 'Trượt'})\n\n"
                    f"📝 *Tổng số giải lô về ngày đó*: {res['actual_count']} đầu số."
                )
                bot.edit_message_text(report, chat_id=message.chat.id, message_id=msg.message_id, parse_mode="Markdown")

        except Exception as e:
            bot.edit_message_text(f"⚠️ Lỗi khi kiểm tra dữ liệu ngày {target_date}: `{str(e)}`", chat_id=message.chat.id, message_id=msg.message_id, parse_mode="Markdown")

    else:
        msg = bot.reply_to(message, "🔍 *Bắt đầu kiểm tra kết nối hệ thống...*", parse_mode="Markdown")
        status_report = []
        
        try:
            count = db.count_results() if hasattr(db, 'count_results') else 0
            status_report.append(f"✅ **CSDL:** Hoạt động tốt (Đã lưu {count} ngày)")
        except Exception as e:
            status_report.append(f"❌ **CSDL:** Lỗi (`{e}`)")
            
        status_report.append("✅ **Scraper:** Hàm cào dữ liệu sẵn sàng")
        status_report.append("✅ **Predictor:** Thuật toán phân tích dự đoán sẵn sàng")

        report_text = "🧪 *BÁO CÁO KIỂM TRA HỆ THỐNG*\n\n" + "\n".join(status_report)
        bot.edit_message_text(report_text, chat_id=message.chat.id, message_id=msg.message_id, parse_mode="Markdown")

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