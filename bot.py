import os
import logging
import yt_dlp
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Điền Token lấy từ @BotFather vào đây
BOT_TOKEN = 8520938638:AAG77o711ySPIMyRurakLMs1xtuASe5UQQU
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Chào bạn! Gửi link video (Facebook Reel, TikTok, YouTube...) vào đây để mình tải nhé.")

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if not url.startswith(("http://", "https://")):
        await update.message.reply_text("Vui lòng gửi một đường link hợp lệ.")
        return

    status_msg = await update.message.reply_text("⏳ Đang xử lý và tải video...")

    # Cấu hình yt-dlp: ưu tiên mp4, giới hạn dưới 50MB để Telegram Bot API gửi được
    ydl_opts = {
        "format": "best[ext=mp4][filesize<50M]/best[ext=mp4]/best",
        "outtmpl": os.path.join(DOWNLOAD_DIR, "%(id)s.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
    }

    filepath = None
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filepath = ydl.prepare_filename(info)

        await status_msg.edit_text("📤 Đang gửi video...")
        with open(filepath, "rb") as video_file:
            await update.message.reply_video(
                video=video_file,
                caption=info.get("title", "Video đã tải xong"),
                supports_streaming=True,
            )
        await status_msg.delete()

    except Exception as e:
        await status_msg.edit_text(f"❌ Lỗi không tải được video: {e}")
    finally:
        # Xóa file tạm trên máy sau khi gửi xong để đỡ tốn dung lượng
        if filepath and os.path.exists(filepath):
            os.remove(filepath)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    print("Bot đang chạy... Nhấn Ctrl+C để dừng.")
    app.run_polling()

if __name__ == "__main__":
    main()
