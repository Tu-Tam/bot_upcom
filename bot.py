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
    get_result
)

from scraper import update_database
from predictor import predict
from backtest import (
    test_single_date,
    run_backtest,
    summarize
)


def format_date(date):

    dt = datetime.strptime(
        date,
        "%Y-%m-%d"
    )

    return dt.strftime(
        "%d/%m/%Y"
    )


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
Backtest một ngày

/backtest 30
Backtest 30 ngày

/stats
Thống kê database
"""

    await update.message.reply_text(
        text
    )


async def update_cmd(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    try:

        count = update_database()

        await update.message.reply_text(
            f"✅ Đã cập nhật {count} kết quả."
        )

    except Exception as e:

        await update.message.reply_text(
            f"❌ Lỗi cập nhật:\n{e}"
        )


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

        target = dt + timedelta(days=1)

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

    for i, (number, score) in enumerate(
        predictions,
        start=1
    ):

        lines.append(
            f"{i}. {number} — {score:.2f}"
        )

    lines.extend([
        "",
        "⚠️ Score chỉ là điểm xếp hạng, "
        "không phải xác suất chắc chắn."
    ])

    await update.message.reply_text(
        "\n".join(lines)
    )


async def test_cmd(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not context.args:

        await update.message.reply_text(
            "Ví dụ:\n"
            "/test 22/08/2026"
        )

        return

    try:

        dt = datetime.strptime(
            context.args[0],
            "%d/%m/%Y"
        )

    except ValueError:

        await update.message.reply_text(
            "Sai định dạng."
        )

        return

    date = dt.strftime(
        "%Y-%m-%d"
    )

    try:

        result = test_single_date(
            date
        )

    except Exception as e:

        await update.message.reply_text(
            f"❌ {e}"
        )

        return

    if result.get("status") == "NO_RESULT":

        await update.message.reply_text(
            "Chưa có kết quả ngày hôm sau."
        )

        return

    predictions = result["predictions"]

    numbers = [
        x[0]
        for x in predictions
    ]

    text = [
        "🧪 BACKTEST",
        "",
        f"Ngày chạy: {format_date(date)}",
        f"Ngày kiểm tra: "
        f"{format_date(result['target_date'])}",
        "",
        "TOP 10:"
    ]

    for i, (number, score) in enumerate(
        predictions,
        1
    ):

        text.append(
            f"{i}. {number} ({score:.2f})"
        )

    text.extend([
        "",
        f"🎯 Kết quả ĐB: {result['actual']}",
        f"2 số cuối: {result['actual']}"
    ])

    if result["hit"]:

        text.extend([
            "",
            "✅ TRÚNG",
            f"Số trúng: {result['actual']}",
            f"Xếp hạng: #{result['rank']}"
        ])

    else:

        text.extend([
            "",
            "❌ KHÔNG TRÚNG"
        ])

    await update.message.reply_text(
        "\n".join(text)
    )


async def backtest_cmd(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    days = 30

    if context.args:

        try:
            days = int(context.args[0])
        except ValueError:
            pass

    await update.message.reply_text(
        f"⏳ Đang backtest {days} ngày..."
    )

    results = run_backtest(
        days
    )

    summary = summarize(
        results
    )

    if not summary:

        await update.message.reply_text(
            "Không đủ dữ liệu."
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
"""

    await update.message.reply_text(
        text
    )


async def stats_cmd(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        f"📚 Database đang có "
        f"{count_results()} ngày dữ liệu."
    )


def main():

    init_db()

    if not TELEGRAM_TOKEN:

        raise RuntimeError(
            "Chưa cấu hình TELEGRAM_TOKEN"
        )

    app = (
        Application
        .builder()
        .token(TELEGRAM_TOKEN)
        .build()
    )

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

    print(
        "XSMB Bot đang chạy..."
    )

    app.run_polling()


if __name__ == "__main__":
    main()
