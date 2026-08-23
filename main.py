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

# === Giữ bot không ngủ trên Render ===
app = Flask('')
@app.route('/')
def giu_chay(): return "✅ Bot lấy ĐỦ TẤT CẢ GIẢI XSMB đang hoạt động!"
def chay_server(): app.run(host="0.0.0.0", port=int(os.environ.get("PORT",8080)))
Thread(target=chay_server).start()

# === THÔNG TIN ĐÃ LƯU SẴN CỦA BẠN ===
BOT_TOKEN = "8520938638:AAEHwQp89_P2slG7YTkod4z6_XvYbgBD7ns"
CHAT_ID = 7064473358
bot = telebot.TeleBot(BOT_TOKEN)

# === Đổi ngẫu nhiên nhận diện trình duyệt giảm bị chặn ===
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
        "Referer":"https://www.google.com/search?q=ketqua+xsmb+day+du+tat+ca+giai",
        "Connection":"keep-alive",
        "Upgrade-Insecure-Requests":"1"
    }

# === Phiên kết nối giữ cookie, tự thử lại khi mạng chập chờn ===
session = requests.Session()
retry_cfg = Retry(total=2, backoff_factor=1.2, status_forcelist=[429,500,502,503,504])
session.mount("https://", HTTPAdapter(max_retries=retry_cfg))

# === Danh sách nguồn ưu tiên lấy đủ danh sách các giải rõ ràng ===
DANH_SACH_NGUON = [
    {"ten":"Minh Ngọc - Đủ giải chuẩn", "link_mau":"https://www.minhngoc.net/kqxs/mien-bac-ngay-{ngay_dinh_dang}.html"},
    {"ten":"Xoso.Com.Vn - Bảng đầy đủ", "link_mau":"https://xoso.com.vn/xsmb-ngay-{ngay_dinh_dang}.html"},
    {"ten":"KQXS VN - Liệt kê rõ từng giải", "link_mau":"https://www.kqxs.vn/mien-bac-ngay-{ngay_dinh_dang}"},
    {"ten":"Xổ Số Dĩ Phát", "link_mau":"https://xosodaiphat.com/ngay-{ngay_dinh_dang}.html"},
    {"ten":"Kết Quả VN", "link_mau":"https://ketqua.vn/ngay-{ngay_dinh_dang}"}
]

def dinh_dang_ngay(ngay_str):
    try:
        dt = datetime.strptime(ngay_str.strip(), "%d %m %Y")
        return dt.strftime("%d-%m-%Y")
    except: return None

def lay_ketqua_day_du(ngay_can):
    ngay_dinh = dinh_dang_ngay(ngay_can)
    if not ngay_dinh:
        return {"thanh_cong":False, "thong_bao":"❌ Sai định dạng!\n👉 Gửi: ngày tháng năm\nVí dụ: 20 08 2026"}

    for stt, nguon in enumerate(DANH_SACH_NGUON,1):
        link = nguon["link_mau"].replace("{ngay_dinh_dang}", ngay_dinh)
        try:
            print(f"🔹 {stt}. Đang lấy ĐỦ TẤT CẢ GIẢI từ: {nguon['ten']} -> {link}")
            resp = session.get(link, headers=lay_header_ngau_nhien(), timeout=18)
            resp.raise_for_status()
            time.sleep(random.uniform(3.2,5.5))

            soup = BeautifulSoup(resp.text, "lxml")

            # === TRÍCH XUẤT ĐỦ 7 GIẢI CHÍNH THEO CẤU TRÚC CHUẨN ===
            bang_ketqua = {}
            # Giải Đặc biệt
            db = soup.select_one("td.giai-dac-biet, .gdb, .dacbiet, td.kqdb")
            bang_ketqua["Đặc biệt"] = re.sub(r"\D","", db.get_text(strip=True)) if db else ""

            # Giải Nhất
            nhat = soup.select_one("td.giai-nhat, .giai1, td:nth-child(2).giai")
            bang_ketqua["Giải Nhất"] = re.sub(r"\D","", nhat.get_text(strip=True)) if nhat else ""

            # Giải Nhì: có 2 số
            danh_sach_nhi = soup.select("td.giai-nhi span, .giai2 span")
            bang_ketqua["Giải Nhì"] = [re.sub(r"\D","",s.get_text(strip=True)) for s in danh_sach_nhi if re.sub(r"\D","",s.get_text(strip=True))]

            # Giải Ba: có 6 số
            danh_sach_ba = soup.select("td.giai-ba span, .giai3 span")
            bang_ketqua["Giải Ba"] = [re.sub(r"\D","",s.get_text(strip=True)) for s in danh_sach_ba if re.sub(r"\D","",s.get_text(strip=True))]

            # Giải Tư: có 4 số
            danh_sach_tu = soup.select("td.giai-tu span, .giai4 span")
            bang_ketqua["Giải Tư"] = [re.sub(r"\D","",s.get_text(strip=True)) for s in danh_sach_tu if re.sub(r"\D","",s.get_text(strip=True))]

            # Giải Năm: có 6 số
            danh_sach_nam = soup.select("td.giai-nam span, .giai5 span")
            bang_ketqua["Giải Năm"] = [re.sub(r"\D","",s.get_text(strip=True)) for s in danh_sach_nam if re.sub(r"\D","",s.get_text(strip=True))]

            # Giải Sáu: có 3 số
            danh_sach_sau = soup.select("td.giai-sau span, .giai6 span")
            bang_ketqua["Giải Sáu"] = [re.sub(r"\D","",s.get_text(strip=True)) for s in danh_sach_sau if re.sub(r"\D","",s.get_text(strip=True))]

            # Giải Bảy: có 4 số
            danh_sach_bay = soup.select("td.giai-bay span, .giai7 span")
            bang_ketqua["Giải Bảy"] = [re.sub(r"\D","",s.get_text(strip=True)) for s in danh_sach_bay if re.sub(r"\D","",s.get_text(strip=True))]

            # Ngày hiển thị rõ
            van_ban_ngay = ""
            for bo_chon_ngay in ["h1", "h2.tieude", ".ngay", "span.title-date", ".date"]:
                tim_n = soup.select_one(bo_chon_ngay)
                if tim_n: van_ban_ngay = tim_n.get_text(strip=True); break

            # Kiểm tra đủ điều kiện có Giải đặc biệt 5 số là chuẩn
            if len(bang_ketqua.get("Đặc biệt","")) ==5:
                return {
                    "thanh_cong":True,
                    "nguon":nguon["ten"],
                    "link_dung":link,
                    "ngay":van_ban_ngay or ngay_dinh,
                    "danh_sach_giai":bang_ketqua
                }
            else:
                print(f"⚠️ {nguon['ten']} chưa lấy đủ số giải đặc biệt chuẩn → chuyển thử trang tiếp theo")

        except Exception as e:
            print(f"⚠️ Lỗi tại {nguon['ten']}: {str(e)[:65]}... chuyển nguồn tiếp theo")
        continue

    return {"thanh_cong":False, "thong_bao":"❌ Đã thử hết danh sách, hôm nay chưa lấy được đủ bảng đầy đủ tất cả các giải, thử lại sau giờ cập nhật chính xác nhé!"}

# === Trả về tin nhắn ĐỊNH DẠNG RÕ RÀNG dễ xem, lưu dữ liệu & phân tích sau này ===
@bot.message_handler(func=lambda m: True)
def xu_ly(msg):
    bot.send_message(msg.chat.id, f"🔄 Đang thu thập BẢNG ĐẦY ĐỦ TẤT CẢ GIẢI: {msg.text}... vui chờ chút nhé!")
    kq = lay_ketqua_day_du(msg.text)
    if kq["thanh_cong"]:
        nd = f"""✅ THÀNH CÔNG LẤY ĐỦ TOÀN BỘ KẾT QUẢ 📋
📅 Ngày: {kq['ngay']}
📌 Nguồn: {kq['nguon']}
🔗 {kq['link_dung']}
━━━━━━━━━━━━━━━━━━━━
🏆 Giải Đặc biệt: {kq['danh_sach_giai']['Đặc biệt']}
🥇 Giải Nhất: {kq['danh_sach_giai']['Giải Nhất']}
🥈 Giải Nhì: {' | '.join(kq['danh_sach_giai']['Giải Nhì'])}
🥉 Giải Ba: {' | '.join(kq['danh_sach_giai']['Giải Ba'])}
🎖️ Giải Tư: {' | '.join(kq['danh_sach_giai']['Giải Tư'])}
🎖️ Giải Năm: {' | '.join(kq['danh_sach_giai']['Giải Năm'])}
🎖️ Giải Sáu: {' | '.join(kq['danh_sach_giai']['Giải Sáu'])}
🎖️ Giải Bảy: {' | '.join(kq['danh_sach_giai']['Giải Bảy'])}
━━━━━━━━━━━━━━━━━━━━
💾 Đã có đủ toàn bộ số rồi: lưu lại dễ tính tần suất, đuôi xuất hiện, xây dựng danh sách ưu tiên theo yêu cầu tiếp theo hoàn hảo hơn!"""
        bot.send_message(msg.chat.id, nd)
    else:
        bot.send_message(msg.chat.id, kq["thong_bao"])

print("🚀 Bot nâng cấp lấy ĐỦ TẤT CẢ CÁC GIẢI đã khởi động!")
bot.polling()
