import requests
from bs4 import BeautifulSoup
import time, random, re
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
from datetime import datetime
import telebot
from flask import Flask
from threading import Thread
import os

# === Giữ bot chạy không ngủ trên Render ===
app = Flask('')
@app.route('/')
def giu_chay(): return "✅ Bot đang hoạt động thử lấy dữ liệu XSMB theo ngày!"
def chay_server(): app.run(host="0.0.0.0", port=int(os.environ.get("PORT",8080)))
Thread(target=chay_server).start()

# === Kết nối Telegram ===
BOT_TOKEN = "8520938638:AAEHwQp89_P2slG7YTkod4z6_XvYbgBD7ns"
CHAT_ID = 7064473358
bot = telebot.TeleBot(BOT_TOKEN)

# === Cấu hình truy cập giảm bị chặn & danh sách nguồn thử tuần tự ===
session = requests.Session()
retry_cfg = Retry(total=3, backoff_factor=1, status_forcelist=[429,500,502,503,504])
session.mount("https://", HTTPAdapter(max_retries=retry_cfg))
HEADERS = {
    "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/128.0.0.0 Safari/537.36",
    "Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language":"vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer":"https://www.google.com/"
}

# Các nguồn có cấu trúc rõ, bạn có thể thêm/bớt/sửa link đúng định dạng theo ngày
DANH_SACH_NGUON = [
    {"ten":"Xổ số Dĩ Phát", "link_mau":"https://xosodaiphat.com/ngay-{ngay_dinh_dang}.html"},
    {"ten":"Kết Quả VN", "link_mau":"https://ketqua.vn/ngay-{ngay_dinh_dang}"},
    {"ten":"Xoso.Me", "link_mau":"https://xoso.me/xsmb-ngay-{ngay_dinh_dang}"}
]

def dinh_dang_ngay(ngay_str):
    """Chuyển 20 08 2026 -> 20-08-2026 dùng điền vào link"""
    try:
        dt = datetime.strptime(ngay_str.strip(), "%d %m %Y")
        return dt.strftime("%d-%m-%Y")
    except: return None

def lay_ketqua_ngay(ngay_can):
    """Thử lần lượt từng nguồn, ghi rõ đang kiểm tra, lấy được trả về dict đầy đủ, thất bại báo rõ lý do"""
    ngay_dinh = dinh_dang_ngay(ngay_can)
    if not ngay_dinh: return {"thanh_cong":False, "thong_bao":"❌ Sai định dạng! Nhập: ngày tháng năm ví dụ: 20 08 2026"}

    for stt, nguon in enumerate(DANH_SACH_NGUON,1):
        link = nguon["link_mau"].replace("{ngay_dinh_dang}", ngay_dinh)
        try:
            print(f"🔹 {stt}. Đang kiểm tra: {nguon['ten']} | {link}")
            resp = session.get(link, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            time.sleep(random.uniform(2.5,4)) # nghỉ tự nhiên không gọi liên tục nhanh quá
            soup = BeautifulSoup(resp.text, "lxml")

            # Trích xuất ngày hiển thị & giải đặc biệt 5 số
            text_ngay = soup.select_one("span.ngay, .ngay-kq, h2.tieude")
            text_ngay = text_ngay.get_text(strip=True) if text_ngay else ""
            gdb = soup.select_one("td.giai-dac-biet, .gdb, .giai-db")
            gdb = gdb.get_text(strip=True) if gdb else ""
            gdb = re.sub(r"\D","",gdb) # lọc chỉ giữ lại số

            if len(gdb)==5:
                return {
                    "thanh_cong":True,
                    "nguon":nguon["ten"],
                    "link_dung":link,
                    "ngay_hien_thi":text_ngay,
                    "giai_dac_biet":gdb
                }
        except Exception as e:
            print(f"⚠️ Không lấy đủ chuẩn từ {nguon['ten']}: {str(e)[:55]}... chuyển thử nguồn tiếp theo")
            continue

    return {"thanh_cong":False, "thong_bao":"❌ Đã kiểm tra hết danh sách nguồn vẫn chưa lấy được đủ dữ liệu chuẩn ngày này"}

# === Lệnh chat đơn giản: người gửi "20 08 2026" -> bot trả kết quả thử lấy được hay không rõ ràng ===
@bot.message_handler(func=lambda m: True)
def xu_ly_yeu_cau(msg):
    bot.send_message(msg.chat.id, f"🔄 Đang kiểm tra lấy dữ liệu: {msg.text}... vui chờ chút nhé")
    kq = lay_ketqua_ngay(msg.text)
    if kq["thanh_cong"]:
        bot.send_message(msg.chat.id,
f"""✅ THÀNH CÔNG lấy được dữ liệu!
📌 Nguồn: {kq['nguon']}
🔗 Liên kết: {kq['link_dung']}
📅 Ngày: {kq['ngay_hien_thi']}
🏆 Giải đặc biệt: {kq['giai_dac_biet']}
→ Bây giờ đã có dữ liệu, bạn tiến hành tính toán thống kê, xếp hạng xác suất theo kế hoạch tiếp theo được rồi!""")
    else:
        bot.send_message(msg.chat.id, kq["thong_bao"]+"\n💡 Lưu ý: có thể trang đang chặn tạm thời, thay đổi chút giờ thử lại hoặc bổ sung thêm link nguồn khác vào danh sách để thử thêm nhé!")

print("🚀 Bot kiểm tra lấy dữ liệu đã khởi động...")
bot.polling()
