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
def giu_chay(): return "✅ Bot lấy đủ toàn bộ kết quả XSMB đang hoạt động ổn định!"
def chay_server(): app.run(host="0.0.0.0", port=int(os.environ.get("PORT",8080)))
Thread(target=chay_server).start()

# === THÔNG TIN ĐÃ LƯU SẴN CỦA BẠN ===
BOT_TOKEN = "8520938638:AAEHwQp89_P2slG7YTkod4z6_XvYbgBD7ns"
CHAT_ID = 7064473358
bot = telebot.TeleBot(BOT_TOKEN)

# === Nhiều bộ nhận diện trình duyệt ngẫu nhiên giảm bị chặn IP máy Render ===
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
        "Referer":"https://www.google.com/search?q=ketqua+xsmb+chinh+thuc"
    }

# === Phiên kết nối giữ cookie, tự thử lại khi mạng quá tải tạm thời ===
session = requests.Session()
retry_cfg = Retry(total=3, backoff_factor=1, status_forcelist=[429,500,502,503,504])
session.mount("https://", HTTPAdapter(max_retries=retry_cfg))

# === MỞ RỘNG DANH SÁCH NGUỒN ưu tiên ketqua.net rất chuẩn + các trang khác bổ sung ===
DANH_SACH_NGUON = [
    {"ten":"Ketqua.Net chuẩn cấu trúc ổn định", "link_mau":"https://ketqua.net/xsmb-ngay-{ngay_dinh_dang}"},
    {"ten":"Minh Ngọc", "link_mau":"https://www.minhngoc.net/kqxs/mien-bac-ngay-{ngay_dinh_dang}.html"},
    {"ten":"Xoso.Com.Vn", "link_mau":"https://xoso.com.vn/xsmb-ngay-{ngay_dinh_dang}.html"},
    {"ten":"Xổ Số Dĩ Phát", "link_mau":"https://xosodaiphat.com/ngay-{ngay_dinh_dang}.html"}
]

def dinh_dang_ngay(ngay_str):
    try: return datetime.strptime(ngay_str.strip(), "%d %m %Y").strftime("%d-%m-%Y")
    except: return None

def lay_ketqua_day_du(ngay_can):
    ngay_dinh = dinh_dang_ngay(ngay_can)
    if not ngay_dinh:
        return {"thanh_cong":False, "thong_bao":"❌ Sai định dạng!\n👉 Gửi: ngày tháng năm\nVí dụ: 17 08 2026"}

    for stt, nguon in enumerate(DANH_SACH_NGUON,1):
        link = nguon["link_mau"].replace("{ngay_dinh_dang}", ngay_dinh)
        try:
            print(f"🔹 {stt}. Đang kiểm tra lấy đủ giải từ: {nguon['ten']}")
            resp = session.get(link, headers=lay_header_ngau_nhien(), timeout=18)
            resp.raise_for_status()
            time.sleep(random.uniform(3.5,6)) # nghỉ tự nhiên lâu hơn chút giảm bị đánh dấu bot
            soup = BeautifulSoup(resp.text, "lxml")

            # === CHÍNH SÁCH QUAN TRỌNG: không bám tên lớp, đọc nội dung chữ trong hàng để nhận biết đúng loại giải ===
            cac_hang = soup.find_all("tr")
            kq = {}
            for hang in cac_hang:
                van_ban_hang = hang.get_text(" ", strip=True).lower()
                danh_sach_so = [re.sub(r"\D","", td.get_text(strip=True)) for td in hang.find_all("td") if len(re.sub(r"\D","", td.get_text(strip=True)))>0]

                if "đặc biệt" in van_ban_hang and len(danh_sach_so)>=1 and len(danh_sach_so[0])==5:
                    kq["Đặc biệt"] = danh_sach_so[0]
                elif "giải nhất" in van_ban_hang and len(danh_sach_so)>=1 and len(danh_sach_so[0])==5:
                    kq["Giải Nhất"] = danh_sach_so[0]
                elif "giải nhì" in van_ban_hang and len(danh_sach_so)>=2:
                    kq["Giải Nhì"] = danh_sach_so[:2]
                elif "giải ba" in van_ban_hang and len(danh_sach_so)>=6:
                    kq["Giải Ba"] = danh_sach_so[:6]
                elif "giải tư" in van_ban_hang and len(danh_sach_so)>=4:
                    kq["Giải Tư"] = danh_sach_so[:4]
                elif "giải năm" in van_ban_hang and len(danh_sach_so)>=6:
                    kq["Giải Năm"] = danh_sach_so[:6]
                elif "giải sáu" in van_ban_hang and len(danh_sach_so)>=3:
                    kq["Giải Sáu"] = danh_sach_so[:3]
                elif "giải bảy" in van_ban_hang and len(danh_sach_so)>=4:
                    kq["Giải Bảy"] = danh_sach_so[:4]

            # === Kiểm tra chặt chẽ đủ TẤT CẢ theo đúng số lượng quy định mới trả thành công ===
            if all(giai in kq for giai in ["Đặc biệt","Giải Nhất","Giải Nhì","Giải Ba","Giải Tư","Giải Năm","Giải Sáu","Giải Bảy"]):
                van_ngay = soup.find("h1") or soup.find("h2")
                van_ngay = van_ngay.get_text(strip=True) if van_ngay else ngay_dinh
                print(f"✅ THÀNH CÔNG lấy đủ chuẩn từ: {nguon['ten']}")
                return {"thanh_cong":True,"nguon":nguon["ten"],"link":link,"ngay":van_ngay,"du_lieu":kq}
            else:
                print(f"⚠️ {nguon['ten']} lấy được nhưng chưa đủ hết các giải → chuyển thử trang tiếp theo")

        except Exception as e:
            print(f"⚠️ Lỗi tại {nguon['ten']}: {str(e)[:60]}... chuyển nguồn tiếp theo")
        continue

    return {"thanh_cong":False,"thong_bao":"❌ Đã thử hết danh sách. Ưu tiên gửi ngày đã công bố kết quả rõ ràng sau 18h30 sẽ dễ lấy đủ dữ liệu nhất nhé!"}

# === Trả kết quả trình bày rõ ràng, đúng cấu trúc chuẩn dễ lưu & tính toán đuôi số sau này ===
@bot.message_handler(func=lambda m: True)
def tra_ket_qua(msg):
    bot.send_message(msg.chat.id,f"🔄 Đang thu thập kiểm tra đủ toàn bộ giải: {msg.text}... vui chờ chút nhé!")
    ketqua = lay_ketqua_day_du(msg.text)
    if ketqua["thanh_cong"]:
        noi_dung = f"""✅ THÀNH CÔNG LẤY ĐỦ CHÍNH XÁC TOÀN BỘ KẾT QUẢ 📋
📅 Ngày: {ketqua['ngay']}
📌 Nguồn: {ketqua['nguon']}
🔗 Liên kết: {ketqua['link']}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏆 Giải Đặc biệt: {ketqua['du_lieu']['Đặc biệt']}
🥇 Giải Nhất: {ketqua['du_lieu']['Giải Nhất']}
🥈 Giải Nhì: {' | '.join(ketqua['du_lieu']['Giải Nhì'])}
🥉 Giải Ba: {' | '.join(ketqua['du_lieu']['Giải Ba'])}
🎖️ Giải Tư: {' | '.join(ketqua['du_lieu']['Giải Tư'])}
🎖️ Giải Năm: {' | '.join(ketqua['du_lieu']['Giải Năm'])}
🎖️ Giải Sáu: {' | '.join(ketqua['du_lieu']['Giải Sáu'])}
🎖️ Giải Bảy: {' | '.join(ketqua['du_lieu']['Giải Bảy'])}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💾 Đủ chuẩn quy định rồi! Tiến hành lưu lại, tính tần suất xuất hiện đuôi số, khoảng nghỉ ngày chưa về để xếp hạng xác suất cao nhất theo kế hoạch phân tích tiếp theo được rồi!"""
        bot.send_message(msg.chat.id, noi_dung)
    else:
        bot.send_message(msg.chat.id, ketqua["thong_bao"])

print("🚀 Bot ưu tiên nhận biết theo tên giải trong nội dung đã khởi động!")
bot.polling()
