# === BOT XỔ SỐ MIỀN BẮC CHẠY ỔN ĐỊNH TRÊN RENDER ===
import os
from flask import Flask
from threading import Thread
import time, telebot, requests
from collections import Counter

# Khởi tạo Flask giữ bot không bị ngủ
app = Flask(__name__)
@app.route('/')
def home():
    return "Bot dang hoat dong san sang!"

def chay_server():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
Thread(target=chay_server).start()

# === Thông tin Bot của bạn ===
BOT_TOKEN = "8520938638:AAEHwQp89_P2slG7YTkod4z6_XvYbgBD7ns"
CHAT_ID = 7064473358
bot = telebot.TeleBot(BOT_TOKEN)

# === Bộ dữ liệu chuẩn cập nhật dễ thay mỗi ngày ===
DU_LIEU = [
    "04","12","25","37","41","58","63","79","82","95",
    "07","15","23","38","42","51","66","72","88","91",
    "03","11","29","44","49","55","61","77","85","92",
    "06","18","22","31","39","47","52","68","75","89",
    "02","14","27","33","50","56","65","73","80","93",
    "09","17","24","35","48","60","71","78","83","97"
]

# === Hàm tính chọn 3 số tốt nhất: tần suất cao + đã nghỉ đủ ngày ===
def chon_3_so(danh_sach):
    dem = Counter(danh_sach)
    lan_cuoi_xuat_hien = {}
    for vi_tri, so in enumerate(reversed(danh_sach)):
        if so not in lan_cuoi_xuat_hien:
            lan_cuoi_xuat_hien[so] = vi_tri
    ds_diem = []
    for st in range(100):
        so = f"{st:02d}"
        tan_suat = dem.get(so, 0)
        so_ngay_nghi = lan_cuoi_xuat_hien.get(so, 60)
        diem = round(tan_suat * 1.3 + min(so_ngay_nghi, 28)*0.55, 2)
        ds_diem.append((-diem, so, tan_suat, so_ngay_nghi))
    ds_diem.sort()
    return [ (s,ts,ng) for _,s,ts,ng in ds_diem[:3] ]

# === Lệnh trả lời tin nhắn ===
@bot.message_handler(func=lambda msg: msg.text.strip()=="Du doan XS")
def tra_ketqua(msg):
    if msg.chat.id != CHAT_ID: return
    bot.send_message(CHAT_ID, "Dang phan tich thong ke 60 ngay gan nhat...")
    top3 = chon_3_so(DU_LIEU)
    bot.send_message(CHAT_ID,f"""KET QUA THONG KE CHON 3 SO TIEM NANG NHAT NGAY MAI
1. So: {top3[0][0]} - Xuat hien {top3[0][1]} lan, da nghi {top3[0][2]} ngay chua ve
2. So: {top3[1][0]} - Xuat hien {top3[1][1]} lan, da nghi {top3[1][2]} ngay chua ve
3. So: {top3[2][0]} - Xuat hien {top3[2][1]} lan, da nghi {top3[2][2]} ngay chua ve

Luu y: Chi la ket qua tinh theo quy luat thong ke du lieu qua khu, mang tinh tham khao vui, khong dam bao chinh xac tuyet doi!""")

@bot.message_handler(func=lambda msg: msg.text.strip()=="Trang thai")
def kiem_tra(msg):
    if msg.chat.id != CHAT_ID: return
    bot.send_message(CHAT_ID, "✅ Bot dang chay on dinh san sang! Go 'Du doan XS' de nhan danh sach so tham khao nhe!")

# === Vong lap chong loi 409 xung dot, tu dong ket noi lai ===
while True:
    try:
        bot.polling(none_stop=True, interval=5, timeout=30)
    except telebot.apihelper.ApiTelegramException as e:
        if "409" in str(e):
            print("Phat hien ban khac dang chay truoc, nghi 15 giay roi khoi dong lai...")
            time.sleep(15)
        else:
            print("Loi ket noi:", str(e)[:60])
            time.sleep(8)
    except Exception as e:
        print("Loi:", e)
        time.sleep(10)
    time.sleep(3)
