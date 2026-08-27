import os
import json
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Import các thuật toán từ predictor.py
from predictor import (
    analyze_and_predict,
    analyze_and_predict_db,
    test_prediction_accuracy,
    test_db_accuracy
)

# Cấu hình logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# --- GIẢ LẬP HÀM LẤY DỮ LIỆU TỪ CSDL / FILE ---
def get_historical_data(limit=100):
    """
    Hàm mẫu lấy lịch sử KQXS.
    Thay thế hàm này bằng kết nối CSDL (SQLite/MySQL/MongoDB) thực tế của bạn.
    """
    try:
        if os.path.exists('data.json'):
            with open('data.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data[:limit]
    except Exception as e:
        logging.error(f"Lỗi đọc dữ liệu: {e}")
    return []

# --- LỆNH /TEST: BACKTEST LÔ (BẠCH THỦ & XIÊN) ---
async def cmd_test_lo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Lấy tham số số ngày test (mặc định 25 ngày nếu không nhập)
        days = 25
        if context.args:
            days = int(context.args[0])

        all_data = get_historical_data(limit=days + 100)
        if len(all_data) < days + 5:
            await update.message.reply_text("⚠️ Không đủ dữ liệu KQXS để thực hiện backtest.")
            return

        report_lines = []
        bt_hits = 0
        x2_hits_total = 0
        x3_hits_total = 0
        x4_hits_total = 0

        # Chạy backtest qua từng ngày
        for i in range(days - 1, -1, -1):
            test_day_data = all_data[i]
            historical = all_data[i+1 : i+101] # 100 kỳ trước ngày test
            
            day_str = test_day_data.get('date', f'Kỳ {i+1}')
            actual_nums = test_day_data.get('numbers', [])

            res = test_prediction_accuracy(historical, actual_nums)
            if not res:
                continue

            # Thống kê kết quả ngày
            bt_status = "✅" if res['bach_thu_hit'] else "❌"
            if res['bach_thu_hit']: bt_hits += 1

            x2_count = res['xien_2_hits_count']
            x2_hits_total += x2_count

            x3_status = "✅" if res['xien_3_hit'] else "❌"
            if res['xien_3_hit']: x3_hits_total += 1

            x4_status = "✅" if res['xien_4_hit'] else "❌"
            if res['xien_4_hit']: x4_hits_total += 1

            report_lines.append(
                f"📅 {day_str}: BT {bt_status} ({res['bach_thu']}) | "
                f"X2: {x2_count}/2 | X3: {x3_status} | X4: {x4_status}"
            )

        # Tổng hợp báo cáo
        bt_rate = (bt_hits / days) * 100
        summary = (
            f"🧪 **BÁO CÁO TEST LÔ (KHUNG {days} NGÀY)**\n"
            f"------------------------------------\n"
            + "\n".join(report_lines) +
            f"\n------------------------------------\n"
            f"📊 **TỔNG KẾT TỶ LỆ TRÚNG:**\n"
            f"🔥 **Bạch Thủ Lô:** {bt_hits}/{days} ngày ({bt_rate:.1f}%)\n"
            f"👯 **Xiên 2:** Trúng tổng {x2_hits_total} cặp\n"
            f"🎯 **Xiên 3:** Trúng {x3_hits_total}/{days} ngày\n"
            f"💎 **Xiên 4:** Trúng {x4_hits_total}/{days} ngày"
        )

        await update.message.reply_text(summary, parse_mode='Markdown')

    except Exception as e:
        logging.error(f"Lỗi lệnh /test: {e}")
        await update.message.reply_text("❌ Đã xảy ra lỗi trong quá trình xử lý test lô.")

# --- LỆNH /TESTDB: BACKTEST ĐỀ ---
async def cmd_test_db(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        days = 25
        if context.args:
            days = int(context.args[0])

        all_data = get_historical_data(limit=days + 100)
        if len(all_data) < days + 5:
            await update.message.reply_text("⚠️ Không đủ dữ liệu KQXS để thực hiện backtest đề.")
            return

        report_lines = []
        d10_hits, d20_hits, d36_hits = 0, 0, 0

        for i in range(days - 1, -1, -1):
            test_day_data = all_data[i]
            historical = all_data[i+1 : i+101]
            
            day_str = test_day_data.get('date', f'Kỳ {i+1}')
            actual_nums = test_day_data.get('numbers', [])

            res = test_db_accuracy(historical, actual_nums)
            if not res:
                continue

            h10 = "✅" if res['is_hit_10'] else "❌"
            h20 = "✅" if res['is_hit_20'] else "❌"
            h36 = "✅" if res['is_hit_36'] else "❌"

            if res['is_hit_10']: d10_hits += 1
            if res['is_hit_20']: d20_hits += 1
            if res['is_hit_36']: d36_hits += 1

            report_lines.append(
                f"📅 {day_str} (Đề: {res['actual_db']})\n"
                f"└ Dàn 10: {h10} | Dàn 20: {h20} | Dàn 36: {h36}"
            )

        summary = (
            f"👑 **BÁO CÁO TEST GIẢI ĐẶC BIỆT ({days} NGÀY)**\n"
            f"------------------------------------\n"
            + "\n".join(report_lines) +
            f"\n------------------------------------\n"
            f"📊 **TỔNG KẾT TỶ LỆ TRÚNG:**\n"
            f"🎯 Dàn 10 số: {d10_hits}/{days} ngày ({(d10_hits/days)*100:.1f}%)\n"
            f"🎯 Dàn 20 số: {d20_hits}/{days} ngày ({(d20_hits/days)*100:.1f}%)\n"
            f"🎯 Dàn 36 số: {d36_hits}/{days} ngày ({(d36_hits/days)*100:.1f}%)"
        )

        await update.message.reply_text(summary, parse_mode='Markdown')

    except Exception as e:
        logging.error(f"Lỗi lệnh /testdb: {e}")
        await update.message.reply_text("❌ Đã xảy ra lỗi trong quá trình xử lý test đề.")

# --- LỆNH /DUDOAN: DỰ ĐOÁN CHO NGÀY HÔM NAY ---
async def cmd_dudoan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        all_data = get_historical_data(limit=100)
        if not all_data:
            await update.message.reply_text("⚠️ Chưa có dữ liệu KQXS.")
            return

        lo_pred = analyze_and_predict(all_data)
        db_pred = analyze_and_predict_db(all_data)

        if not lo_pred or not db_pred:
            await update.message.reply_text("❌ Không thể phân tích dữ liệu.")
            return

        # Format danh sách Xiên
        str_x2 = "\n".join([f"  • Cặp {i+1}: {pair[0]} - {pair[1]}" for i, pair in enumerate(lo_pred['xien_2'])])
        str_x3 = " - ".join(lo_pred['xien_3'])
        str_x4 = " - ".join(lo_pred['xien_4'])

        msg = (
            f"🔮 **DỰ ĐOÁN KẾT QUẢ XỔ SỐ HÔM NAY**\n"
            f"------------------------------------\n"
            f"🎯 **BẠCH THỦ LÔ:** `{lo_pred['bach_thu']}`\n\n"
            f"👯 **XIÊN 2:**\n{str_x2}\n\n"
            f"🥉 **XIÊN 3:** `{str_x3}`\n"
            f"🏅 **XIÊN 4:** `{str_x4}`\n"
            f"------------------------------------\n"
            f"👑 **DÀN ĐẶC BIỆT:**\n"
            f"📌 Dàn 10 số: `{', '.join(db_pred['top_10_db'])}`\n"
            f"📌 Dàn 20 số: `{', '.join(db_pred['top_20_db'])}`\n"
            f"📌 Dàn 36 số: `{', '.join(db_pred['top_36_db'])}`"
        )

        await update.message.reply_text(msg, parse_mode='Markdown')

    except Exception as e:
        logging.error(f"Lỗi dự đoán: {e}")
        await update.message.reply_text("❌ Có lỗi xảy ra khi tính toán dự đoán.")

# --- HÀM MAIN KHỞI CHẠY BOT ---
def main():
    # Thay 'YOUR_TELEGRAM_BOT_TOKEN' bằng Token thực tế của bạn
    TOKEN = os.getenv("BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")
    
    application = Application.builder().token(TOKEN).build()

    # Đăng ký các lệnh
    application.add_handler(CommandHandler("test", cmd_test_lo))
    application.add_handler(CommandHandler("testdb", cmd_test_db))
    application.add_handler(CommandHandler("dudoan", cmd_dudoan))

    logging.info("Bot đang chạy...")
    application.run_polling()

if __name__ == '__main__':
    main()