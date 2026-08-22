# === BOT XỔ SỐ MIỀN BẮC HOÀN CHỈNH CHẠY ỔN ĐỊNH RENDER ===
import os
from flask import Flask
from threading import Thread
import time, telebot, requests
from collections import Counter
from datetime import datetime, timedelta

# Khởi tạo Flask giữ bot không bị ngắt khi không hoạt động
app = Flask(__name__)
@app.route('/')
def giu_song():
    return "✅ Bot dang hoat dong on dinh!"

def chay_server():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
Thread(target=chay_server).start()

# === THÔNG TIN BOT CỦA BẠN ===
BOT_TOKEN = "8520938638:AAEHwQp89_P2slG7YTkod4z6_XvYbgBD7ns"
CHAT_ID = 7064473358
bot = telebot.TeleBot(BOT_TOKEN)

# === DANH SÁCH DỮ LIỆU 60 NGÀY GẦN NHẤT - DỄ THAY SỐ MỖI NGÀY ===
DU_LIEU = [
    "04","12","25","37","41","58","63","79","82","95",
    "07","15","23","38","42","51","66","72","88","91",
    "03","11","29","44","49","55","61","77","85","92",
    "06","18","22","31","39","47","52","68","75","89",
    "02","14","27","33","50","56","65","73","80","93",
    "09","17","24","35","48","60","71","78","83","97"
]

# === HÀM TÍNH CHỌN 3 SỐ TỐT NHẤT: TẦN SUẤT CAO + ĐÃ NGHỈ ĐỦ NGÀY ===
def chon_3_so_tot(danh_sach):
    dem = Counter(danh_sach)
    lan_xuat_hien_cuoi = {}
    for vi_tri, so in enumerate(reversed(danh_sach)):
        if so not in lan_xuat_hien_cuoi:
            lan_xuat_hien_cuoi[so] = vi_tri
    ds_diem = []
    for st in range(100):
        so = f"{st:02d}"
        tan_suat = dem.get(so, 0)
        so_ngay_nghi = lan_xuat_hien_cuoi.get(so, 60)
        diem_tong = round(tan_suat * 1.3 + min(so_ngay_nghi, 28) * 0.55, 2)
        ds_diem.append((-diem_tong, so, tan_suat, so_ngay_nghi))
    ds_diem.sort()
    return [ (s, ts, ng) for _, s, ts, ng in ds_diem[:3] ]

# === XỬ LÝ LỆNH KIỂM TRA TRẠNG THÁI ===
@bot.message_handler(func=lambda msg: msg.text.strip() == "Trang thai")
def tra_loi_trangthai(msg):
    if msg.chat.id != CHAT_ID: return
    bot.send_message(CHAT_ID, "✅ Bot dang chay lien tuc san sang! Go 'Du doan XS' de nhan danh sach so tham khao nhe!")

# === XỬ LÝ LỆNH DỰ ĐOÁN: TỰ LẤY ĐÚNG NGÀY THEO GIỜ VIỆT NAM ===
@bot.message_handler(func=lambda msg: msg.text.strip() == "Du doan XS")
def tra_ketqua_dudoan(msg):
    if msg.chat.id != CHAT_ID: return
    bot.send_message(CHAT_ID, "Dang phan tich thong ke 60 ngay gan nhat...")
    top3 = chon_3_so_tot(DU_LIEU)
    
    # === CHÍNH XÁC MÚI GIỜ +7 VIỆT NAM, HIỂN THỊ NGÀY THÁNG NĂM RÕ RÀNG ===
    gio_vn_chuan = datetime.utcnow() + timedelta(hours=7)
    chuoi_ngay = f"ngay {gio_vn_chuan.day} thang {gio_vn_chuan.month} nam {gio_vn_chuan.year}"
    
    bot.send_message(CHAT_ID,f"""KET QUA THONG KE CHON 3 SO TIEM NANG NHAT {chuoi_ngay}
1. So: {top3[0][0]} - Xuat hien {top3[0][1]} lan, da nghi {top3[0][2]} ngay chua ve
2. So: {top3[1][0]} - Xuat hien {top3[1][1]} lan, da nghi {top3[1][2]} ngay chua ve
3. So: {top3[2][0]} - Xuat hien {top3[2][1]} lan, da nghi {top3[2][2]} ngay chua ve

Luu y: Chi la ket qua tinh theo quy luat thong ke du lieu da co, mang tinh tham khao vui, khong dam bao chinh xac tuyet doi!""")

# === VÒNG LẮNG NGHE CHỐNG LỖI 409 XUNG ĐỘT, TỰ KHỞI ĐỘNG LẠI MỀM MẠI ===
while True:
    try:
        bot.polling(none_stop=True, interval=5, timeout=30)
    except telebot.apihelper.ApiTelegramException as loi:
        if "409" in str(loi):
            print("Phat hien ban chay khac, nghi 15 giay roi khoi dong lai...")
            time.sleep(15)
        else:
            print("Loi ket noi:", str(loi)[:60])
            time.sleep(8)
    except Exception as loi_khac:
        print("Loi:", loi_khac)
        time.sleep(10)
    time.sleep(3)
