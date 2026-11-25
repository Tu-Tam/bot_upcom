import logging
import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
import yt_dlp

BOT_TOKEN = "8520938638:AAG77o711ySPIMyRurakLMs1xtuASe5UQQU"
DOWNLOAD_DIR = "downloads"
MAX_FILE_SIZE_MB = 50

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Lưu tạm link theo user_id khi người dùng bấm chọn định dạng
USER_LINKS: dict[int, str] = {}

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Chào bạn! Hãy gửi link video (Facebook Reel, TikTok, YouTube...) vào đây.\n"
        "Mình sẽ hiện nút để bạn chọn tải *Video (.mp4)* hoặc *Tách âm thanh (.mp3)*.",
        parse_mode="Markdown",
    )


async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    url = update.message.text.strip()
    if not url.startswith(("http://", "https://")):
        await update.message.reply_text(
            "Vui lòng gửi một đường link hợp lệ bắt đầu bằng http:// hoặc https://."
        )
        return

    user_id = update.effective_user.id
    USER_LINKS[user_id] = url

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎬 Tải Video (.mp4)", callback_data="mode_video"),
            InlineKeyboardButton("🎵 Tách nhạc/tiếng (.mp3)", callback_data="mode_audio"),
        ]
    ])

    await update.message.reply_text(
        "Đã nhận link! Bạn muốn tải định dạng nào?",
        reply_markup=keyboard,
    )


def _cleanup_files(media_id: str | None, extra_paths: list[str]):
    for path in extra_paths:
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass

    if media_id:
        for fname in os.listdir(DOWNLOAD_DIR):
            if fname.startswith(media_id):
                full_path = os.path.join(DOWNLOAD_DIR, fname)
                if os.path.exists(full_path):
                    try:
                        os.remove(full_path)
                    except OSError:
                        pass


async def handle_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query or not query.message:
        return

    await query.answer()

    user_id = query.from_user.id
    url = USER_LINKS.get(user_id)
    if not url:
        await query.edit_message_text(
            "Link đã hết hạn hoặc không tìm thấy. Vui lòng gửi lại link mới."
        )
        return

    mode = query.data
    await query.edit_message_text("⏳ Đang xử lý và tải file, vui lòng đợi...")

    filepath: str | None = None
    media_id: str | None = None

    try:
        if mode == "mode_video":
            ydl_opts = {
                "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
                "outtmpl": os.path.join(DOWNLOAD_DIR, "%(id)s.%(ext)s"),
                "merge_output_format": "mp4",
                "noplaylist": True,
                "quiet": True,
            }
        else:
            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": os.path.join(DOWNLOAD_DIR, "%(id)s.%(ext)s"),
                "noplaylist": True,
                "quiet": True,
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }],
            }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            media_id = str(info.get("id", "")) if info else None
            base_path = os.path.splitext(ydl.prepare_filename(info))[0]

            if mode == "mode_audio" and os.path.exists(base_path + ".mp3"):
                filepath = base_path + ".mp3"
            elif os.path.exists(base_path + ".mp4"):
                filepath = base_path + ".mp4"
            else:
                filepath = ydl.prepare_filename(info)

        if not filepath or not os.path.exists(filepath):
            await query.edit_message_text("❌ Không tìm thấy file sau khi tải.")
            return

        file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
        if file_size_mb > MAX_FILE_SIZE_MB:
            await query.edit_message_text(
                f"⚠️ File nặng {file_size_mb:.1f} MB, vượt giới hạn {MAX_FILE_SIZE_MB} MB của Telegram Bot API."
            )
            return

        await query.edit_message_text("📤 Đang gửi file về cho bạn...")
        title = (info.get("title") if info else None) or "File tải về"
        caption = title[:1000]

        if mode == "mode_video":
            with open(filepath, "rb") as f:
                await context.bot.send_video(
                    chat_id=query.message.chat_id,
                    video=f,
                    caption=caption,
                    supports_streaming=True,
                )
        else:
            with open(filepath, "rb") as f:
                await context.bot.send_audio(
                    chat_id=query.message.chat_id,
                    audio=f,
                    title=title[:200],
                )

        await query.delete_message()

    except Exception as e:
        logger.exception("Lỗi khi xử lý link %s", url)
        await query.edit_message_text(f"❌ Lỗi khi tải: {e}")
    finally:
        _cleanup_files(media_id, [filepath] if filepath else [])


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Exception while handling an update:", exc_info=context.error)


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    app.add_handler(CallbackQueryHandler(handle_choice, pattern="^mode_"))
    app.add_error_handler(error_handler)

    print("Bot Telegram đang chạy... Nhấn Ctrl+C để dừng.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
