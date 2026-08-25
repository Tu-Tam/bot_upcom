def khoi_tao_du_lieu():
        with db_lock:
            try:
                print("📦 Bắt đầu xây dựng kho dữ liệu 90 ngày...")
                so_ngay = tai_90_ngay_gan_nhat()
                print(f"✅ Đã xây dựng xong: {so_ngay} ngày hợp lệ!")
                
                if CHAT_ID:
                    bot.send_message(
                        CHAT_ID,
                        f"🚀 **BOT XSMB ĐÃ KHỞI ĐỘNG!**\n"
                        f"📂 Dữ liệu sẵn sàng: {so_ngay} ngày.\n"
                        f"Gõ /stats hoặc /help để kiểm tra."
                    )
            except Exception as err:
                print(f"⚠️ Quá trình cào dữ liệu gặp lỗi: {err}")
                # Gửi thông báo lỗi về Telegram nếu cào dữ liệu thất bại
                if CHAT_ID:
                    bot.send_message(CHAT_ID, f"⚠️ Bot đã bật nhưng cào dữ liệu thất bại: {err}")