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
def giu_chay(): return "✅ Bot sửa lại lấy đủ đúng số lượng từng giải XSMB đang chạy!"
def chay_server(): app.run(host="0.0.0.0", port=int(os.environ.get("PORT",8080)))
Thread(target=chay_server).start()

# === THÔNG TIN CỦA BẠN ĐỂ NGUYÊN ===
BOT_TOKEN = "8520938638:AAEHwQp89_P2slG7YTkod4z6_XvYbgBD7ns"
CHAT_ID = 7064473358
bot = telebot.TeleBot(BOT_TOKEN)

# === Nhiều bộ nhận diện trình duyệt ngẫu nhiên giảm bị chặn ===
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:130.0) Gecko/20100101 Firefox/130.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Edge/129.0.0.0"
]
def lay_header_ngau_nhien():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language":"vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer":"https://www.google.com/"
    }

session = requests.Session()
retry_cfg = Retry(total=2, backoff_factor=1.2, status_forcelist=[429,500,502,503,504])
session.mount("https://", HTTPAdapter(max_retries=retry_cfg))

# === Nguồn ưu tiên, thêm thử chọn theo cấu trúc bảng chung ===
DANH_SACH_NGUON = [
    {"ten":"Minh Ngọc", "link_mau":"https://www.minhngoc.net/kqxs/mien-bac-ngay-{ngay_dinh_dang}.html"},
    {"ten":"Xoso.Com.Vn", "link_mau":"https://xoso.com.vn/xsmb-ngay-{ngay_dinh_dang}.html"},
    {"ten":"KQXS.VN", "link_mau":"https://www.kqxs.vn/mien-bac-ngay-{ngay_dinh_dang}"},
    {"ten":"Xổ số Dĩ Phát", "link_mau":"https://xosodaiphat.com/ngay-{ngay_dinh_dang}.html"},
    {"ten":"Kết Quả VN", "link_mau":"https://ketqua.vn/ngay-{ngay_dinh_dang}"}
]

def dinh_dang_ngay(ngay_str):
    try: return datetime.strptime(ngay_str.strip(),"%d %m %Y").strftime("%d-%m-%Y")
    except: return None

def lay_ketqua_day_du(ngay_can):
    ngay_dinh = dinh_dang_ngay(ngay_can)
    if not ngay_dinh: return {"thanh_cong":False,"thong_bao":"❌ Sai định dạng! Gửi: ví dụ 17 08 2026"}

    for stt, nguon in enumerate(DANH_SACH_NGUON,1):
        link = nguon["link_mau"].replace("{ngay_dinh_dang}",ngay_dinh)
        try:
            print(f"🔹 {stt}. Kiểm tra: {nguon['ten']} -> {link}")
            resp = session.get(link, headers=lay_header_ngau_nhien(), timeout=18)
            resp.raise_for_status()
            time.sleep(random.uniform(3,5))
            soup = BeautifulSoup(resp.text,"lxml")

            # === CẢI TIẾM QUAN TRỌNG: thử chọn bảng kết quả chung trước, lấy theo hàng <tr> thay vì tên lớp riêng lẻ dễ đổi ===
            bang_chinh = None
            for bo_chon_bang in ["table.bang-kq", "table.table-kq", "table.kqxs", "div.bang-kq table", "table"]:
                bang_chinh = soup.select_one(bo_chon_bang)
                if bang_chinh: break
            if not bang_chinh:
                print(f"⚠️ {nguon['ten']} không tìm thấy bảng kết quả rõ → chuyển tiếp")
                continue

            cac_hang = bang_chinh.find_all("tr")
            du_lieu = {}
            # Đọc từng hàng lọc đúng tên giải & lấy số chỉ giữ lại chữ số
            for hang in cac_hang:
                nd_hang = hang.get_text(" ",strip=True)
                so_ds = [re.sub(r"\D","",td.get_text(strip=True)) for td in hang.find_all("td") if re.sub(r"\D","",td.get_text(strip=True))]
                if "đặc biệt" in nd_hang.lower() and len(so_ds)>=1 and len(so_ds[0])==5: du_lieu["Đặc biệt"]=so_ds[0]
                elif "nhất" in nd_hang.lower() and len(so_ds)>=1 and len(so_ds[0])==5: du_lieu["Giải Nhất"]=so_ds[0]
                elif "nhì" in nd_hang.lower() and len(so_ds)>=2: du_lieu["Giải Nhì"]=so_ds[:2]
                elif "ba" in nd_hang.lower() and len(so_ds)>=6: du_lieu["Giải Ba"]=so_ds[:6]
                elif "tư" in nd_hang.lower() and len(so_ds)>=4: du_lieu["Giải Tư"]=so_ds[:4]
                elif "năm" in nd_hang.lower() and len(so_ds)>=6: du_lieu["Giải Năm"]=so_ds[:6]
                elif "sáu" in nd_hang.lower() and len(so_ds)>=3: du_lieu["Giải Sáu"]=so_ds[:3]
                elif "bảy" in nd_hang.lower() and len(so_ds)>=4: du_lieu["Giải Bảy"]=so_ds[:4]

            # === KIỂM TRA CHÍNH XÁC ĐỦ ĐÚNG SỐ LƯỢNG QUY ĐỊNH mới trả về thành công ===
            if all(k in du_lieu for k in ["Đặc biệt","Giải Nhất","Giải Nhì","Giải Ba","Giải Tư","Giải Năm","Giải Sáu","Giải Bảy"]):
                van_ngay = soup.select_one("h1,h2.tieude,.ngay,span.title-date")
                van_ngay = van_ngay.get_text(strip=True) if van_ngay else ngay_dinh
                print(f"✅ Đủ chuẩn từ {nguon['ten']}")
                return {"thanh_cong":True,"nguon":nguon["ten"],"link_dung":link,"ngay":van_ngay,"ds":du_lieu}
            else:
                print(f"⚠️ {nguon['ten']} lấy được nhưng chưa đủ đủ tất cả các giải theo số lượng quy định → thử tiếp trang khác")

        except Exception as e:
            print(f"⚠️ Lỗi tại {nguon['ten']}: {str(e)[:60]}... chuyển nguồn tiếp theo")
        continue

    return {"thanh_cong":False,"thong_bao":"❌ Đã thử hết danh sách. Mẹo: thử lại vào giờ sau 18h30 khi kết quả cập nhật đầy đủ nhất, hoặc tôi có thể bổ sung thêm trang mới khi bạn chia sẻ trang xem ổn định thường dùng nhé!"}

# === Trả lời trình bày rõ ràng đúng cấu trúc ===
@bot.message_handler(func=lambda m:True)
def xu_ly(msg):
    bot.send_message(msg.chat.id,f"🔄 Thu thập kiểm tra đủ số lượng từng giải: {msg.text}... chờ chút nhé!")
    kq=lay_ketqua_day_du(msg.text)
    if kq["thanh_cong"]:
        nd=f"""✅ THÀNH CÔNG LẤY ĐỦ CHÍNH XÁC TẤT CẢ GIẢI 📋
📅 Ngày: {kq['ngay']}
📌 Nguồn: {kq['nguon']}
🔗 {kq['link_dung']}
━━━━━━━━━━━━━━━━━━━━
🏆 Giải Đặc biệt(5 số): {kq['ds']['Đặc biệt']}
🥇 Giải Nhất(5 số): {kq['ds']['Giải Nhất']}
🥈 Giải Nhì(2 số): {' | '.join(kq['ds']['Giải Nhì'])}
🥉 Giải Ba(6 số): {' | '.join(kq['ds']['Giải Ba'])}
🎖️ Giải Tư(4 số): {' | '.join(kq['ds']['Giải Tư'])}
🎖️ Giải Năm(6 số): {' | '.join(kq['ds']['Giải Năm'])}
🎖️ Giải Sáu(3 số): {' | '.join(kq['ds']['Giải Sáu'])}
🎖️ Giải Bảy(4 số): {' | '.join(kq['ds']['Giải Bảy'])}
━━━━━━━━━━━━━━━━━━━━
💾 Đủ chuẩn quy định rồi, lưu bảng này tính tần suất đuôi, khoảng nghỉ xuất hiện xây dựng danh sách ưu tiên theo yêu cầu tiếp theo được rồi!"""
        bot.send_message(msg.chat.id,nd)
    else: bot.send_message(msg.chat.id,kq["thong_bao"])

print("🚀 Bot nâng cấp chọn theo bảng & kiểm tra đủ số lượng đã khởi động!")
bot.polling()
