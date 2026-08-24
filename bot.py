import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes
)

from config import TELEGRAM_TOKEN

from database import (
    init_db,
    count_results,
    get_result,
    get_results
)

from scraper import update_database
from predictor import predict

from backtest import (
    test_single_date,
    run_backtest,
    summarize
)


# ============================================================
# HTTP SERVER CHO RENDER
# ============================================================

class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):

        self.send_response(200)

        self.send_header(
            "Content-Type",
            "text/plain; charset=utf-8"
        )

        self.end_headers()

        self.wfile.write(
            b"XSMB Bot is running!"
        )

    def do_HEAD(self):

        self.send_response(200)

        self.send_header(
            "Content-Type",
            "text/plain; charset=utf-8"
        )

        self.end_headers()

    def log_message(
        self,
        format,
        *args
    ):
        return


def start_web_server():

    port = int(
        os.environ.get(
            "PORT",
            10000
        )
    )

    server = HTTPServer(
        ("0.0.0.0", port),
        HealthHandler
    )

    print(
        f"Web server đang chạy trên port {port}"
    )

    server.serve_forever()


# ============================================================
# FORMAT DATE
# ============================================================

def format_date(date):

    dt = datetime.strptime(
        date,
        "%Y-%m-%d"
    )

    return dt.strftime(
        "%d/%m/%Y"
    )


# ============================================================
# START
# ============================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    text = """
🤖 XSMB ANALYTICS BOT

Lệnh:

/update
Cập nhật dữ liệu

/predict
Dự đoán ngày tiếp theo

/predict DD/MM/YYYY
Dự đoán ngày sau ngày nhập

/test DD/MM/YYYY
Dự đoán và kiểm tra kết quả ngày hôm sau

/backtest 30
Backtest 30 ngày

/stats
Thống kê database
"""

    await update.message.reply_text(
        text
    )


# ============================================================
# UPDATE
# ============================================================

async def update_cmd(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    try:

        print("UPDATE: bắt đầu")

        count = update_database()

        print(
            f"UPDATE: hoàn thành, {count} kết quả"
        )

        await update.message.reply_text(
            f"✅ Đã cập nhật {count} kết quả."
        )

    except Exception as e:

        print(
            f"UPDATE ERROR: {repr(e)}"
        )

        await update.message.reply_text(
            f"❌ Lỗi cập nhật:\n{e}"
        )


# ============================================================
# PREDICT
# ============================================================

async def predict_cmd(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if context.args:

        try:

            dt = datetime.strptime(
                context.args[0],
                "%d/%m/%Y"
            )

        except ValueError:

            await update.message.reply_text(
                "Sai định dạng.\n"
                "Ví dụ: /predict 24/08/2026"
            )

            return

        target = dt + timedelta(
            days=1
        )

    else:

        target = datetime.now() + timedelta(
            days=1
        )

    target_date = target.strftime(
        "%Y-%m-%d"
    )

    try:

        predictions = predict(
            target_date,
            10
        )

    except Exception as e:

        await update.message.reply_text(
            f"❌ {e}"
        )

        return

    lines = [
        "🔮 DỰ ĐOÁN XSMB",
        "",
        f"Ngày: {format_date(target_date)}",
        "",
        "TOP 10:"
    ]

    for i, (
        number,
        score
    ) in enumerate(
        predictions,
        start=1
    ):

        lines.append(
            f"{i}. "
            f"{str(number).zfill(2)} "
            f"— {score:.2f}"
        )

    lines.extend([
        "",
        "⚠️ Score chỉ là điểm xếp hạng, "
        "không phải xác suất chắc chắn."
    ])

    await update.message.reply_text(
        "\n".join(lines)
    )


# ============================================================
# TEST
# ============================================================

async def test_cmd(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    # ========================================================
    # KIỂM TRA THAM SỐ
    # ========================================================

    if not context.args:

        await update.message.reply_text(
            "Ví dụ:\n"
            "/test 22/08/2026"
        )

        return

    # ========================================================
    # PARSE DATE
    # ========================================================

    try:

        dt = datetime.strptime(
            context.args[0],
            "%d/%m/%Y"
        )

    except ValueError:

        await update.message.reply_text(
            "❌ Sai định dạng ngày.\n\n"
            "Ví dụ:\n"
            "/test 22/08/2026"
        )

        return

    prediction_date = dt.strftime(
        "%Y-%m-%d"
    )

    # ========================================================
    # NGÀY CẦN DỰ ĐOÁN
    # ========================================================

    target_dt = dt + timedelta(
        days=1
    )

    target_date = target_dt.strftime(
        "%Y-%m-%d"
    )

    # ========================================================
    # DỰ ĐOÁN
    # ========================================================

    try:

        predictions = predict(
            target_date,
            top_n=10
        )

    except Exception as e:

        print(
            f"TEST PREDICT ERROR: {repr(e)}"
        )

        await update.message.reply_text(
            f"❌ Không thể tạo dự đoán:\n{e}"
        )

        return

    if not predictions:

        await update.message.reply_text(
            "❌ Predictor không trả về kết quả."
        )

        return

    # ========================================================
    # LẤY KẾT QUẢ DATABASE
    # ========================================================

    try:

        actual_row = get_result(
            target_date
        )

    except Exception as e:

        print(
            f"TEST DATABASE ERROR: {repr(e)}"
        )

        await update.message.reply_text(
            f"❌ Lỗi đọc database:\n{e}"
        )

        return

    # ========================================================
    # CHUẨN HÓA TOP 10
    # ========================================================

    prediction_numbers = []

    for number, score in predictions:

        prediction_numbers.append(
            (
                str(number).zfill(2),
                score
            )
        )

    numbers = [
        number
        for number, score
        in prediction_numbers
    ]

    # ========================================================
    # CHƯA CÓ KẾT QUẢ
    # ========================================================

    if actual_row is None:

        lines = [
            "⏳ ĐANG ĐỢI XỔ",
            "",
            f"Ngày dự đoán: "
            f"{format_date(target_date)}",
            "",
            "Chưa có kết quả XSMB.",
            "",
            "⚠️ Chưa thể đánh giá "
            "TRÚNG / KHÔNG TRÚNG.",
            "",
            "🔮 TOP 10 DỰ ĐOÁN:"
        ]

        for i, (
            number,
            score
        ) in enumerate(
            prediction_numbers,
            start=1
        ):

            lines.append(
                f"{i}. "
                f"{number} "
                f"— {score:.2f}"
            )

        await update.message.reply_text(
            "\n".join(lines)
        )

        return

    # ========================================================
    # ĐÃ CÓ KẾT QUẢ
    # ========================================================

    try:

        special = str(
            actual_row[1]
        ).zfill(5)

        actual = str(
            actual_row[2]
        ).zfill(2)

    except Exception as e:

        print(
            f"TEST RESULT PARSE ERROR: "
            f"{repr(e)}"
        )

        await update.message.reply_text(
            "❌ Dữ liệu kết quả trong "
            "database không hợp lệ."
        )

        return

    # ========================================================
    # SO SÁNH
    # ========================================================

    hit = actual in numbers

    rank = None

    if hit:

        rank = (
            numbers.index(actual)
            + 1
        )

    # ========================================================
    # TẠO KẾT QUẢ
    # ========================================================

    if hit:

        lines = [
            "✅ TRÚNG",
            "",
            f"Ngày dự đoán: "
            f"{format_date(target_date)}",
            "",
            f"🎯 Kết quả ĐB: {special}",
            f"🔢 2 số cuối: {actual}",
            "",
            f"🏆 Số trúng: {actual}",
            f"📊 Xếp hạng: #{rank}"
        ]

    else:

        lines = [
            "❌ KHÔNG TRÚNG",
            "",
            f"Ngày dự đoán: "
            f"{format_date(target_date)}",
            "",
            f"🎯 Kết quả ĐB: {special}",
            f"🔢 2 số cuối: {actual}",
            "",
            "Không có số trúng "
            "trong TOP 10."
        ]

    # ========================================================
    # TOP 10
    # ========================================================

    lines.extend([
        "",
        "🔮 TOP 10 DỰ ĐOÁN:"
    ])

    for i, (
        number,
        score
    ) in enumerate(
        prediction_numbers,
        start=1
    ):

        marker = ""

        if number == actual:

            marker = " ← 🎯"

        lines.append(
            f"{i}. "
            f"{number} "
            f"— {score:.2f}"
            f"{marker}"
        )

    # ========================================================
    # GỬI TELEGRAM
    # ========================================================

    await update.message.reply_text(
        "\n".join(lines)
    )


# ============================================================
# BACKTEST
# ============================================================

async def backtest_cmd(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    days = 30

    if context.args:

        try:

            days = int(
                context.args[0]
            )

        except ValueError:

            await update.message.reply_text(
                "❌ Số ngày không hợp lệ.\n"
                "Ví dụ: /backtest 30"
            )

            return

    if days <= 0:

        await update.message.reply_text(
            "❌ Số ngày phải lớn hơn 0."
        )

        return

    await update.message.reply_text(
        f"⏳ Đang backtest {days} ngày..."
    )

    try:

        results = run_backtest(
            days
        )

        summary = summarize(
            results
        )

    except Exception as e:

        print(
            f"BACKTEST ERROR: {repr(e)}"
        )

        await update.message.reply_text(
            f"❌ Lỗi backtest:\n{e}"
        )

        return

    if not summary:

        await update.message.reply_text(
            "Không đủ dữ liệu để backtest."
        )

        return

    text = f"""
📊 BACKTEST

Số ngày:
{summary['days']}

Có trúng:
{summary['hits']}

Hit rate:
{summary['hit_rate'] * 100:.2f}%

Top 1:
{summary['top1'] * 100:.2f}%

Top 3:
{summary['top3'] * 100:.2f}%

Top 5:
{summary['top5'] * 100:.2f}%

Top 10:
{summary['top10'] * 100:.2f}%
"""

    await update.message.reply_text(
        text
    )


# ============================================================
# STATS
# ============================================================

async def stats_cmd(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    try:

        rows = get_results(
            limit=20
        )

        total = count_results()

    except Exception as e:

        print(
            f"STATS ERROR: {repr(e)}"
        )

        await update.message.reply_text(
            f"❌ Lỗi đọc database:\n{e}"
        )

        return

    if not rows:

        await update.message.reply_text(
            "📚 Database đang trống."
        )

        return

    lines = [
        "📚 DATABASE",
        "",
        f"Tổng số ngày: {total}",
        "",
        "20 kết quả gần nhất:",
        ""
    ]

    for row in rows:

        date = row[0]
        special = row[1]
        last2 = row[2]
        weekday = row[3]

        lines.append(
            f"{date} | "
            f"ĐB: {special} | "
            f"2 số cuối: {last2} | "
            f"weekday: {weekday}"
        )

    await update.message.reply_text(
        "\n".join(lines)
    )


# ============================================================
# MAIN
# ============================================================

def main():

    # ========================================================
    # DATABASE
    # ========================================================

    init_db()

    # ========================================================
    # TELEGRAM TOKEN
    # ========================================================

    if not TELEGRAM_TOKEN:

        raise RuntimeError(
            "Chưa cấu hình TELEGRAM_TOKEN"
        )

    # ========================================================
    # HTTP SERVER CHO RENDER
    # ========================================================

    web_thread = threading.Thread(
        target=start_web_server,
        daemon=True
    )

    web_thread.start()

    # ========================================================
    # TELEGRAM APPLICATION
    # ========================================================

    app = (
        Application
        .builder()
        .token(
            TELEGRAM_TOKEN
        )
        .build()
    )

    # ========================================================
    # HANDLERS
    # ========================================================

    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    app.add_handler(
        CommandHandler(
            "update",
            update_cmd
        )
    )

    app.add_handler(
        CommandHandler(
            "predict",
            predict_cmd
        )
    )

    app.add_handler(
        CommandHandler(
            "test",
            test_cmd
        )
    )

    app.add_handler(
        CommandHandler(
            "backtest",
            backtest_cmd
        )
    )

    app.add_handler(
        CommandHandler(
            "stats",
            stats_cmd
        )
    )

    # ========================================================
    # START BOT
    # ========================================================

    print(
        "XSMB Bot đang chạy..."
    )

    app.run_polling()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()
