# === MÃ CHUẨN CHẠY ỔN ĐỊNH TRÊN RENDER ===
import os
import random
from flask import Flask
from threading import Thread
import time
import telebot
import requests
from bs4 import BeautifulSoup
from collections import Counter
from datetime import datetime, timedelta

app = Flask(__name__)
@app.route('/')
def giu_song():
    return "✅ Bot đang hoạt động ổn định: chống chặn, lấy dữ liệu & nhận bổ sung, phân tích xổ số + đánh giá UPCOM thành công!"

def chay_server():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

Thread(target=chay_server).start()

BOT_TOKEN = "8520938638:AAEHwQp89_P2slG7YTkod4z6_XvYbgBD7ns"
CHAT_ID = 7064473358
bot = telebot.TeleBot(BOT_TOKEN)
DA_CO_DU_LIEU = {}
DS_LINK_NGUON = [
    "https://ketqua.vn/xo-so-mien-bac/ngay-{d}-{m}-{y}",
    "https://xoso.me/xsmb-{d}-{m}-{y}",
    "https://xoso.com.vn/kqxs-mien-bac-ngay-{d}-{m}-{y}.html"
]

def tinh_diem_chuan(danh_sach_duoi):
    dem_so_lan = Counter(danh_sach_duoi)
    vi_tri_tung_lan = {}
    for vt, ma in enumerate(danh_sach_duoi):
        vi_tri_tung_lan.setdefault(ma, []).append(vt)
    ds_diem = []
    for ma in dem_so_lan.keys():
        so_lan = dem_so_lan[ma]
        vi_tri = vi_tri_tung_lan[ma]
        if len(vi_tri) < 2:
            diem = round(so_lan * 2.5, 2)
        else:
            khoang_cach = []
            for i in range(1, len(vi_tri)):
                khoang_cach.append(vi_tri[i] - vi_tri[i-1])
            chenh_lech = max(khoang_cach) - min(khoang_cach) if max(khoang_cach) != min(khoang_cach) else 1
            do_deu = round(10 / (1 + chenh_lech), 2)
            diem = round(so_lan * 4.0 + do_deu * 10, 2)
        ds_diem.append((-diem, ma, so_lan))
    ds_diem.sort()
    top3 = [(m, sl) for _, m, sl in ds_diem[:3]]
    top20 = [m for _, m, _ in ds_diem[:20]]
    return top3, top20

def lay_an_toan(ngay_obj):
    khoa_ngay = ngay_obj.strftime("%d/%m/%Y")
    if khoa_ngay in DA_CO_DU_LIEU:
        return DA_CO_DU_LIEU[khoa_ngay]
    DS_HEADER = [
        {"User-Agent": "Mozilla/5.0 (Linux; Android 14; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36",
         "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7", "Referer": "https://www.google.com/"},
        {"User-Agent": "Mozilla/5.0 (Linux; Android 13; Redmi Note12) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36",
         "Accept-Language": "vi-VN,vi;q=0.9", "Referer": "https://ketqua.vn/"}
    ]
    for link_mau in DS_LINK_NGUON:
        link_tao = link_mau.format(d=ngay_obj.day, m=ngay_obj.month, y=ngay_obj.year)
        for _ in range(2):
            try:
                res = requests.get(link_tao, headers=random.choice(DS_HEADER), timeout=9)
                if res.status_code != 200:
                    time.sleep(random.uniform(0.6,1.1))
                    continue
                soup = BeautifulSoup(res.text, "html.parser")
                ds_so = []
                for the in soup.select("span.prize-number, span.number, div.prize span"):
                    chuoi = the.get_text(strip=True)
                    if chuoi.isdigit() and len(chuoi)>=2:
                        ds_so.append(chuoi[-2:])
                if len(ds_so)>=25:
                    DA_CO_DU_LIEU[khoa_ngay] = ds_so
                    return ds_so
            except:
                time.sleep(random.uniform(0.5,1.0))
    return None

@bot.message_handler(func=lambda msg: msg.text.strip().startswith("Luu du lieu:"))
def xu_ly_luu_ban_gui(msg):
    try:
        noi_dung = msg.text.strip().replace("Luu du lieu:","").strip()
        phan_ngay = noi_dung.split("|")[0].replace("Ngày","").strip()
        danh_sach_duoi = [d.strip() for d in noi_dung.split("|")[1].replace("Đuôi:","").strip().split(",") if d.strip() and len(d.strip())==2]
        ngay_chuan = datetime.strptime(phan_ngay,"%d/%m/%Y").strftime("%d/%m/%Y")
        DA_CO_DU_LIEU[ngay_chuan] = danh_sach_duoi
        bot.send_message(msg.chat.id,f"✅ ĐÃ LƯU THÀNH CÔNG NGÀY: {ngay_chuan}\nSố đuôi nhận được: {len(danh_sach_duoi)} số, sẵn sàng phân tích chung!")
    except:
        bot.send_message(msg.chat.id,"⚠️ Dùng mẫu: Luu du lieu: Ngày 22/08/2026 | Đuôi: 00,07,09,06,... nhé!")

@bot.message_handler(func=lambda msg: len(msg.text.strip().split())==3 and all(s.isdigit() for s in msg.text.strip().split()))
def phan_tich_ngay_yeu_cau(msg):
    try:
        tach = msg.text.strip().split()
        ngay_moc = datetime(int(tach[2]),int(tach[1]),int(tach[0]))
        bot.send_message(msg.chat.id,"🔄 Đang truy cập an toàn luân phiên nguồn & chờ nhẹ lấy đủ dữ liệu liên tục... chờ chút nhé!")
        tap_hop = []
        for lui in range(60):
            ngay_lui = ngay_moc - timedelta(days=lui)
            kq = lay_an_toan(ngay_lui)
            if kq:
                tap_hop.extend(kq)
            time.sleep(random.uniform(0.22,0.4))
        if len(tap_hop)<40:
            bot.send_message(msg.chat.id,f"ℹ️ Đã gom được {len(tap_hop)} số hợp lệ! Gửi bổ sung vài ngày gần nhất theo mẫu là đủ phân tích ngay nhé!")
            return
        top3,top20 = tinh_diem_chuan(tap_hop)
        ngay_sau = ngay_moc + timedelta(days=1)
        bot.send_message(msg.chat.id,f"""✅===== HOÀN THÀNH PHÂN TÍCH =====
📅 Tổng hợp đủ dữ liệu tích lũy đến: {ngay_moc.strftime('%d/%m/%Y')}
👉 THAM KHẢO CHỌN SỐ CHO NGÀY: {ngay_sau.strftime('%d/%m/%Y')}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏆 TOP 3 ĐUÔI CÓ QUY LUẬT NHẤT:
🥇 Đuôi {top3[0][0]} – xuất hiện {top3[0][1]} lần | Tần suất cao nhất + chu kỳ đều ổn định nhất
🥈 Đuôi {top3[1][0]} – xuất hiện {top3[1][1]} lần | Quy luật tốt thứ hai
🥉 Đuôi {top3[2][0]} – xuất hiện {top3[2][1]} lần | Đáng tin cậy thứ ba

📋 Danh sách 20 đuôi tốt khác:
▫️ {'  ▫️ '.join(top20)}

⚠️ Chỉ mang tính tham khảo vui chơi giải trí!
""")
    except Exception as loi:
        bot.send_message(msg.chat.id,"⚠️ Nhập đúng 3 số Ngày Tháng Năm cách khoảng trắng là được nhé!")

API_KEY_ALPHA = ["SYHGO5Z8DE4RAU8E","52MWBOYE0RSLQE8E","N8TO30AM8DVVGDE7"]
DANH_SACH_UPCOM = ["SHB","HDB","TCB","VPB","MBB","SSB","EIB","VIX","MBS","VCI","SSI","ACB","BID","VCB"]

def lay_danh_gia_cp(ma):
    for apikey in API_KEY_ALPHA:
        try:
            url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={ma}.VN&apikey={apikey}&outputsize=compact"
            res = requests.get(url, timeout=10).json()
            if "Time Series" in res:
                ds_ngay = sorted(res["Time Series (Daily)"].items(), reverse=True)[:14]
                gia_dong = [float(v["4. close"]) for _, v in ds_ngay]
                if len(gia_dong)>=10:
                    ema5 = round(sum(gia_dong[:5])/5,2)
                    ema10 = round(sum(gia_dong[:10])/10,2)
                    xu_huong = "📈 Xu hướng tăng tốt" if ema5>ema10 else "📉 Cần theo dõi chờ cải thiện"
                    diem = round(min(10,5+(ema5-ema10)*100/ema10),1)
                    gia_hien_tai = gia_dong[0]
                    chot_loi = round(gia_hien_tai*1.03,2)
                    cat_lo = round(gia_hien_tai*0.97,2)
                    return f"{ma} | Điểm: {diem}/10 | {xu_huong}\n💵 Giá hiện tại: {gia_hien_tai:,}\n🎯 Giá chốt lời: {chot_loi:,}\n🛡️ Giá cắt lỗ an toàn: {cat_lo:,}"
        except:
            continue
    return f"⚠️ Tạm chưa lấy được dữ liệu {ma}"

@bot.message_handler(func=lambda msg: msg.text.strip() == "Danh gia UPCOM")
def danh_gia_nhom(msg):
    if msg.chat.id != CHAT_ID:
        return
    bot.send_message(CHAT_ID,"🔄 Đang lấy dữ liệu & đánh giá theo thang điểm 10...")
    ketqua = []
    for ma in DANH_SACH_UPCOM:
        ketqua.append(lay_danh_gia_cp(ma))
        time.sleep(1.2)
    bot.send_message(CHAT_ID,"\n\n".join(ketqua))

@bot.message_handler(func=lambda msg: msg.text.strip().startswith("DG "))
def danh_gia_mot_ma(msg):
    if msg.chat.id != CHAT_ID:
        return
    ma = msg.text.strip()[3:].upper().strip()
    bot.send_message(CHAT_ID, lay_danh_gia_cp(ma))

@bot.message_handler(func=lambda msg: msg.text.strip() == "Trang thai")
def kiem_tra(msg):
    if msg.chat.id != CHAT_ID:
        return
    bot.send_message(CHAT_ID,"✅ **Đang hoạt động ổn định:**\n📌 Truy cập chống chặn hiệu quả, luân phiên nguồn lấy dữ liệu\n📌 Nhận lưu nhanh dữ liệu bạn gửi bổ sung khi trang tạm chặn\n📌 Phân tích xổ số + đánh giá cổ phiếu UPCOM đủ chức năng đã yêu cầu!")

while True:
    try:
        bot.polling(none_stop=True, interval=5, timeout=60)
    except Exception as loi:
        print(f"Kết nối lại: {loi}")
        time.sleep(10)
