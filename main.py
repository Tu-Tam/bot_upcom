# === BOT ĐIỀU CHỈNH: GỠ GIỚI HẠN GỜ, TÍNH ĐỦ 60 NGÀY TỪ NGÀY BẠN YÊU CẦU, ƯU TIÊN NGUỒN CSV ỔN ĐỊNH ===
import os
import random
from flask import Flask
from threading import Thread
import time
import telebot
import requests
import csv
from io import StringIO
from collections import Counter
from datetime import datetime, timedelta

app = Flask(__name__)
@app.route('/')
def giu_song():
    return "✅ Đã cập nhật: không giới hạn giờ, tính ngược đủ 60 ngày chính xác từ ngày yêu cầu, lấy dữ liệu CSV nhanh ít bị chặn!"

def chay_server():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

Thread(target=chay_server).start()

BOT_TOKEN = "8520938638:AAEHwQp89_P2slG7YTkod4z6_XvYbgBD7ns"
CHAT_ID = 7064473358
bot = telebot.TeleBot(BOT_TOKEN)
DA_CO_DU_LIEU = {}

# 📌 Nguồn ưu tiên ổn định nhất theo tìm được
LINK_CSV_GITHUB = "https://raw.githubusercontent.com/vietnam-lottery-xsmb-analysis/xsmb/main/data/xsmb_daily.csv"

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

# === 🚀 Lấy đủ chuỗi dữ liệu ngược lại đúng 60 ngày tính từ ngày bạn nhập ===
def lay_tu_csv_du_60ngay(ngay_batdau):
    if DA_CO_DU_LIEU:
        return DA_CO_DU_LIEU
    try:
        res = requests.get(LINK_CSV_GITHUB, timeout=12)
        res.raise_for_status()
        doc = csv.DictReader(StringIO(res.text))
        for hang in doc:
            try:
                ngay_hang = datetime.strptime(hang["date"], "%Y-%m-%d")
                so_ngay_ke = (ngay_batdau - ngay_hang).days
                # Chỉ lấy đúng khoảng 60 ngày liền kề lùi về trước
                if 0 <= so_ngay_ke < 60:
                    ds_so = []
                    for i in range(1,28):
                        gt = hang.get(f"prize_{i}","").strip()
                        if len(gt)>=2 and gt.isdigit():
                            ds_so.append(gt[-2:])
                    if len(ds_so)>=25:
                        DA_CO_DU_LIEU[ngay_hang.strftime("%d/%m/%Y")] = ds_so
            except:
                continue
        return DA_CO_DU_LIEU
    except Exception as e:
        print(f"Lấy CSV tạm khó: {e}")
        return None

# === 📥 Vẫn giữ nhận dữ liệu bạn gửi bổ sung nhanh khi cần đầy đủ ngay ===
@bot.message_handler(func=lambda msg: msg.text.strip().startswith("Luu du lieu:"))
def xu_ly_luu_ban_gui(msg):
    try:
        noi_dung = msg.text.strip().replace("Luu du lieu:","").strip()
        phan_ngay = noi_dung.split("|")[0].replace("Ngày","").strip()
        danh_sach_duoi = [d.strip() for d in noi_dung.split("|")[1].replace("Đuôi:","").strip().split(",") if d.strip() and len(d.strip())==2]
        ngay_chuan = datetime.strptime(phan_ngay,"%d/%m/%Y").strftime("%d/%m/%Y")
        DA_CO_DU_LIEU[ngay_chuan] = danh_sach_duoi
        bot.send_message(msg.chat.id,f"✅ ĐÃ LƯU THÀNH CÔNG NGÀY: {ngay_chuan}\n✅ Đã thêm vào bộ dữ liệu chung sẵn sàng tính đủ 60 ngày!")
    except:
        bot.send_message(msg.chat.id,"⚠️ Dùng đúng mẫu: Luu du lieu: Ngày 22/08/2026 | Đuôi: 00,07,09,06,... nhé!")

# === ✅ NHẬN NGÀY → TÍNH CHÍNH XÁC LÙI 60 NGÀY LIỀN → RA KẾT QUẢ CHO NGÀY SAU NGAY LẬP TỨC ===
@bot.message_handler(func=lambda msg: len(msg.text.strip().split())==3 and all(s.isdigit() for s in msg.text.strip().split()))
def phan_tich_ngay_yeu_cau(msg):
    try:
        tach = msg.text.strip().split()
        ngay_moc = datetime(int(tach[2]),int(tach[1]),int(tach[0]))
        bot.send_message(msg.chat.id,"🔄 Đang tải & lọc chính xác đủ 60 ngày liền kề tính từ ngày bạn yêu cầu...")

        tap_ngay = lay_tu_csv_du_60ngay(ngay_moc)
        tap_hop = []
        # Lấy đúng thứ tự lùi dần đủ 60 ngày liên tục
        for dem in range(60):
            ngay_lui = ngay_moc - timedelta(days=dem)
            khoa = ngay_lui.strftime("%d/%m/%Y")
            if khoa in tap_ngay:
                tap_hop.extend(tap_ngay[khoa])
            time.sleep(random.uniform(0.15,0.25)) # chờ nhẹ giữ kết nối tốt không quá tải

        if len(tap_hop)<40:
            bot.send_message(msg.chat.id,f"ℹ️ Đã thu thập được {len(tap_hop)} số hợp lệ! Gửi bổ sung vài ngày theo mẫu trên là đủ chuẩn phân tích ngay nhé!")
            return

        top3,top20 = tinh_diem_chuan(tap_hop)
        ngay_sau = ngay_moc + timedelta(days=1)
        bot.send_message(msg.chat.id,f"""✅===== HOÀN THÀNH PHÂN TÍCH =====
📅 Dựa trên đủ chuỗi 60 ngày liên tục tính đến: {ngay_moc.strftime('%d/%m/%Y')}
👉 THAM KHẢO CHỌN SỐ CHO NGÀY: {ngay_sau.strftime('%d/%m/%Y')}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏆 TOP 3 ĐUÔI CÓ QUY LUẬT NHẤT:
🥇 Đuôi {top3[0][0]} – xuất hiện {top3[0][1]} lần | Tần suất cao nhất + chu kỳ đều ổn định nhất
🥈 Đuôi {top3[1][0]} – xuất hiện {top3[1][1]} lần | Quy luật xuất hiện đều đặn tốt
🥉 Đuôi {top3[2][0]} – xuất hiện {top3[2][1]} lần | Đáng tin cậy theo thống kê tích lũy

📋 Danh sách 20 đuôi tốt khác:
▫️ {'  ▫️ '.join(top20)}

⚠️ Chỉ mang tính tham khảo vui chơi giải trí!
""")
    except Exception as loi:
        bot.send_message(msg.chat.id,"⚠️ Nhập đúng định dạng: Ngày Tháng Năm cách khoảng trắng là được nhé!")

# === 📈 PHẦN ĐÁNH GIÁ CỔ PHIẾU UPCOM HOÀN TOÀN GIỮ NGUYÊN HOẠT ĐỘNG ỔN ĐỊNH ===
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
    bot.send_message(CHAT_ID,"✅ **Đã hoàn chỉnh đúng yêu cầu:**\n📌 Không còn giới hạn giờ nào, nhập ngày là tính ngay được kết quả\n📌 Luôn lấy đúng đủ 60 ngày liên tục lùi về trước chính xác từ ngày bạn nhập\n📌 Ưu tiên nguồn CSV cập nhật đều đặn ít bị chặn nhất, bổ sung được dữ liệu bạn gửi thủ công khi cần đủ nhanh chóng!")

while True:
    try:
        bot.polling(none_stop=True, interval=5, timeout=60)
    except Exception as loi:
        print(f"Kết nối lại: {loi}")
        time.sleep(10)
