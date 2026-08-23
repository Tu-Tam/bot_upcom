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

# === Giữ bot không bị ngủ trên Render ===
app = Flask('')
@app.route('/')
def giu_chay(): return "✅ Bot lấy dữ liệu XSMB đang hoạt động ổn định!"
def chay_server(): app.run(host="0.0.0.0", port=int(os.environ.get("PORT",8080)))
Thread(target=chay_server).start()

# === THÔNG TIN ĐÃ LƯU SẴN CỦA BẠN ===
BOT_TOKEN = "8520938638:AAEHwQp89_P2slG7YTkod4z6_XvYbgBD7ns"
CHAT_ID = 7064473358
bot = telebot.TeleBot(BOT_TOKEN)

# === Nhiều bộ nhận diện trình duyệt đổi ngẫu nhiên mỗi lần truy cập giảm bị chặn ===
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:130.0) Gecko/20100101 Firefox/130.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Edge/129.0.0.0"
]

def lay_header_ngau_nhien():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language":"vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding":"gzip, deflate, br",
        "Referer":"https://www.google.com/search?q=ketqua+xsmb",
        "Connection":"keep-alive",
        "Upgrade-Insecure-Requests":"1"
    }

# === Tạo phiên giữ cookie, tự thử lại khi lỗi mạng tạm thời ===
session = requests.Session()
retry_cfg = Retry(total=2, backoff_factor=1.2, status_forcelist=[429,500,502,503,504])
session.mount("https://", HTTPAdapter(max_retries=retry_cfg))

# === Danh sách nhiều nguồn uy tín thử tuần tự, tăng cơ hội lấy được ===
DANH_SACH_NGUON = [
    {"ten":"Minh Ngọc Uy Tín", "link_mau":"https://www.minhngoc.net/kqxs/mien-bac-ngay-{ngay_dinh_dang}.html"},
    {"ten":"Xổ Số .Com.Vn", "link_mau":"https://xoso.com.vn/xsmb-ngay-{ngay_dinh_dang}.html"},
    {"ten":"KQXS VN", "link_mau":"https://www.kqxs.vn/mien-bac-ngay-{ngay_dinh_dang}"},
    {"ten":"Xổ Số Dĩ Phát", "link_mau":"https://xosodaiphat.com/ngay-{ngay_dinh_dang}.html"},
    {"ten":"Kết Quả VN", "link_mau":"https://ketqua.vn/ngay-{ngay_dinh_dang}"}
]

def dinh_dang_ngay(ngay_str):
    """Chuyển '20 08 2026' thành '20-08-2026' khớp định dạng liên kết"""
    try:
        dt = datetime.strptime(ngay_str.strip(), "%d %m %Y")
        return dt.strftime("%d-%m-%Y")
    except: return None

def lay_ketqua_ngay(ngay_can):
    ngay_dinh = dinh_dang_ngay(ngay_can)
    if not ngay_dinh:
        return {"thanh_cong":False, "thong_bao":"❌ Sai định dạng!\n👉 Gửi đúng: ngày tháng năm\nVí dụ: 20 08 2026"}

    for stt, nguon in enumerate(DANH_SACH_NGUON,1):
        link = nguon["link_mau"].replace("{ngay_dinh_dang}", ngay_dinh)
        try:
            print(f"🔹 {stt}. Đang kiểm tra: {nguon['ten']} -> {link}")
            resp = session.get(link, headers=lay_header_ngau_nhien(), timeout=15)
            resp.raise_for_status()
            time.sleep(random.uniform(3,5.5)) # nghỉ tự nhiên như người xem không bị đánh dấu nhanh quá

            soup = BeautifulSoup(resp.text, "lxml")
            # Thử nhiều kiểu chọn vị trí giải đặc biệt khác nhau phù hợp nhiều trang
            gdb = None
            for bo_chon in ["td.giai-dac-biet", ".gdb", "span.db", "td:last-child", ".dacbiet", "td.kqdb"]:
                tim = soup.select_one(bo_chon)
                if tim:
                    gdb = re.sub(r"\D","", tim.get_text(strip=True))
                    if len(gdb)==5: break

            van_ban_ngay = ""
            for bo_chon_ngay in ["h1", "h2.tieude", ".ngay", "span.title-date", ".date"]:
                tim_n = soup.select_one(bo_chon_ngay)
                if tim_n:
                    van_ban_ngay = tim_n.get_text(strip=True)
                    break

            if gdb and len(gdb)==5:
                return {
                    "thanh_cong":True,
                    "nguon":nguon["ten"],
                    "link_dung":link,
                    "ngay_hien_thi":van_ban_ngay or ngay_dinh,
                    "giai_dac_biet":gdb
                }
            else:
                print(f"⚠️ Kết nối được {nguon['ten']} nhưng chưa tìm đúng đủ 5 số giải đặc biệt → chuyển thử trang tiếp theo")

        except requests.exceptions.HTTPError as e:
            print(f"⚠️ Trang {nguon['ten']} bị chặn/từ chối truy cập: Mã lỗi {e.response.status_code} → chuyển thử tiếp")
        except Exception as e:
            print(f"⚠️ Lỗi xử lý tại {nguon['ten']}: {str(e)[:60]}... chuyển thử tiếp")
        continue

    return {
        "thanh_cong":False,
        "thong_bao":"""❌ Đã kiểm tra hết danh sách trang hôm nay chưa lấy trực tiếp được!
💡 Nguyên nhân thường gặp: IP máy Render bị chặn tạm thời / trang cập nhật giao diện mới
✅ Giải pháp nhanh có dữ liệu ngay: Sử dụng bộ dữ liệu lịch sử CSV GitHub ổn định ít chặn nhất để phân tích thống kê 60 ngày trước nhé!
📌 Hoặc thử lại sau vài giờ / vào giờ công bố kết quả chính xác sẽ dễ thành công hơn!"""
    }

# === Xử lý tin nhắn bạn gửi ngày tháng năm, trả kết quả rõ ràng ===
@bot.message_handler(func=lambda m: True)
def xu_ly_yeu_cau(msg):
    bot.send_message(msg.chat.id, f"🔄 Đang kiểm tra lấy dữ liệu: {msg.text}... vui chờ chút nhé!")
    kq = lay_ketqua_ngay(msg.text)
    if kq["thanh_cong"]:
        bot.send_message(msg.chat.id,
f"""✅ THÀNH CÔNG LẤY ĐƯỢC DỮ LIỆU! 🎉
📌 Nguồn lấy: {kq['nguon']}
🔗 Liên kết: {kq['link_dung']}
📅 Ngày tra cứu: {kq['ngay_hien_thi']}
🏆 Giải đặc biệt: {kq['giai_dac_biet']}
→ Có đủ số rồi, lưu lại và tiến hành tính thống kê, xếp hạng đuôi số có xác suất cao nhất theo kế hoạch tiếp theo được rồi!""")
    else:
        bot.send_message(msg.chat.id, kq["thong_bao"])

print("🚀 Bot lấy dữ liệu XSMB đã khởi động thành công với thông tin của bạn!")
bot.polling()
