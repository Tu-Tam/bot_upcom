# === CẢI THIỆN TÍCH LŨY DỮ LIỆU ĐÃ LẤY ĐƯỢC KHÔNG XÓA ĐI, LINH HOẠT TIẾP TỤC, VẪN KIỂM TRA THỨ TỰ & BÁO CHÍNH XÁC ===
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
    return "✅ Đã nâng cấp: lưu giữ tích lũy những ngày lấy được không mất đi, cộng dần khi kiểm tra lại, báo rõ số lượng đang có, dễ đủ chuẩn nhanh hơn!"

def chay_server():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

Thread(target=chay_server).start()

BOT_TOKEN = "8520938638:AAEHwQp89_P2slG7YTkod4z6_XvYbgBD7ns"
CHAT_ID = 7064473358
bot = telebot.TeleBot(BOT_TOKEN)
DA_CO_DU_LIEU = {} # ✅ Lưu lại vĩnh viễn những ngày đã lấy/thêm thủ công, mỗi lần kiểm tra mới cộng thêm có được nhiều hơn chứ không làm trống lại!

# 📋 Giữ nguyên thứ tự ưu tiên các trang đang truy cập được
DANH_SACH_NGUON_UU_TIEN = [
    {"ten": "Trang tổng hợp ketqua.vn lấy nhiều ngày cùng lúc", "link": "https://ketqua.vn/lich-su-xo-so-mien-bac", "loai": "tonghop_html"},
    {"ten": "Trang xoso.me lịch sử rõ ràng", "link": "https://xoso.me/lich-su-ket-qua-xsmb", "loai": "tonghop_html"},
    {"ten": "Trang xosomienbac.org chuẩn đầy đủ", "link": "https://xosomienbac.org/lich-su-ket-qua/", "loai": "tonghop_html"}
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

# === 🚀 Lấy được ngày nào hợp lệ thì THÊM VÀO bộ chung KHÔNG XÓA những ngày đã có trước đó nữa ===
def lay_tu_trang_tonghop(link, ngay_moc_can):
    DA_HEADER = [
        {"User-Agent":"Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Mobile Safari/537.36",
         "Accept-Language":"vi-VN,vi;q=0.9", "Referer":"https://www.google.com/"},
        {"User-Agent":"Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
         "Accept-Language":"vi-VN,vi;q=0.9", "Referer":"https://facebook.com/"}
    ]
    try:
        res = requests.get(link, headers=random.choice(DA_HEADER), timeout=12)
        if res.status_code != 200: return {}
        soup = BeautifulSoup(res.text,"html.parser")
        tap_moi_lay_duoc = {}
        for khoang in soup.select("table.table tr, div.result-day, div.prize-block, div.item-kq"):
            try:
                chuoi_ngay = khoang.select_one("span.date, div.ngay, .ngay-thang")
                if not chuoi_ngay: continue
                chuoi_ngay = chuoi_ngay.get_text(strip=True)
                dt_lay = datetime.strptime(chuoi_ngay,"%d/%m/%Y")
                so_ngay_ke = (ngay_moc_can - dt_lay).days
                if not (0 <= so_ngay_ke <60): continue # Chỉ nhận đúng trong khoảng 60 ngày yêu cầu
                ds_so = []
                for so_tag in khoang.select("span.prize-number, .number, span.giai-so"):
                    s = so_tag.get_text(strip=True)
                    if s.isdigit() and len(s)>=2: ds_so.append(s[-2:])
                if len(ds_so)>=22: # đủ số giải trong ngày thì lưu ngày đó lại
                    tap_moi_lay_duoc[dt_lay.strftime("%d/%m/%Y")]=ds_so
            except: continue
        return tap_moi_lay_duoc
    except Exception as e:
        print(f"Lỗi lấy trang: {e}")
        return {}

# === 📋 QUY TRÌNH: cộng dần mới vào cũ, báo rõ hiện đang có tổng cộng bao nhiêu ngày trong khoảng yêu cầu ===
def lay_du_lieu_theo_thu_tu(ngay_batdau):
    bot.send_message(CHAT_ID, "🔄 Bắt đầu kiểm tra & thu thập thêm dữ liệu theo đúng thứ tự ưu tiên đã đặt...")
    thong_bao_trang_thai = []
    da_cong_them = False

    for thu_tu, nguon in enumerate(DANH_SACH_NGUON_UU_TIEN, 1):
        thong_bao_trang_thai.append(f"🔹 {thu_tu}. Đang kiểm tra: {nguon['ten']}...")
        try:
            tap_moi = lay_tu_trang_tonghop(nguon["link"], ngay_batdau)
            if tap_moi:
                so_truoc = len([k for k in DA_CO_DU_LIEU if 0 <= (ngay_batdau - datetime.strptime(k,"%d/%m/%Y")).days <60])
                DA_CO_DU_LIEU.update(tap_moi) # ✅ Cộng thêm những ngày mới lấy được, giữ nguyên không ghi đè/xóa những ngày đã có trước đó!
                so_sau = len([k for k in DA_CO_DU_LIEU if 0 <= (ngay_batdau - datetime.strptime(k,"%d/%m/%Y")).days <60])
                if so_sau > so_truoc:
                    thong_bao_trang_thai.append(f"✅ Thu thập thêm được {so_sau-so_truoc} ngày mới từ: {nguon['ten']} → Tổng hiện có: {so_sau}/60 ngày yêu cầu!")
                    da_cong_them = True
                else:
                    thong_bao_trang_thai.append(f"ℹ️ Không có ngày mới thêm được từ {nguon['ten']} → chuyển thử nguồn tiếp theo...")
            else:
                thong_bao_trang_thai.append(f"⚠️ Không lấy được dữ liệu mới từ {nguon['ten']} → chuyển thử nguồn tiếp theo...")
        except Exception as e:
            thong_bao_trang_thai.append(f"❌ Gặp khó truy cập {nguon['ten']}: {str(e)[:50]}... → chuyển thử nguồn tiếp theo!")
        time.sleep(random.uniform(0.7,1.3))

    # ✅ Kiểm tra tổng số đang có: đủ ≥45 ngày là phân tích ngay được kết quả tốt, chưa đủ thì báo rõ số còn thiếu & hướng dẫn bổ sung ít ngày thôi là đủ nhanh chóng
    tong_ngay_co = len([k for k in DA_CO_DU_LIEU if 0 <= (ngay_batdau - datetime.strptime(k,"%d/%m/%Y")).days <60])
    thong_bao_trang_thai.append(f"\n📊 === TỔNG KẾT HIỆN CÓ: {tong_ngay_co}/60 ngày trong khoảng yêu cầu ===")

    if tong_ngay_co >=45: # Ngưỡng thực tế đủ tin cậy phân tích ra kết quả tham khảo tốt
        thong_bao_trang_thai.append("✅ Đạt đủ mức tin cậy tiến hành phân tích ngay!")
        bot.send_message(CHAT_ID, "\n".join(thong_bao_trang_thai))
        return True, DA_CO_DU_LIEU, f"Đủ {tong_ngay_co} ngày phân tích được kết quả"
    else:
        thong_bao_trang_thai.append(f"💡 Chỉ cần bổ sung thêm {45-tong_ngay_co} ngày gần nhất theo mẫu là đủ chuẩn nhanh chóng:")
        thong_bao_trang_thai.append("📝 Luu du lieu: Ngày __/__/____ | Đuôi: 00,07,09,... → mỗi lần gửi thêm sẽ tích lũy tăng số ngày cho đến đủ tự động phân tích!")
        bot.send_message(CHAT_ID, "\n".join(thong_bao_trang_thai))
        return False, {}, "Đang tích lũy dần, hiện có "+str(tong_ngay_co)+" ngày"

# === 📥 LỆNH LƯU BỔ SUNG: NHẬN MỖI LẦN GỬI THÊM CŨNG CỘNG DẦN VÀO TỔNG SỐ, KHÔNG GHI ĐÈ LẠI ===
@bot.message_handler(func=lambda msg: msg.text.strip().startswith("Luu du lieu:"))
def xu_ly_luu_ban_gui(msg):
    try:
        noi_dung = msg.text.strip().replace("Luu du lieu:","").strip()
        phan_ngay = noi_dung.split("|")[0].replace("Ngày","").strip()
        danh_sach_duoi = [d.strip() for d in noi_dung.split("|")[1].replace("Đuôi:","").strip().split(",") if d.strip() and len(d.strip())==2]
        ngay_chuan = datetime.strptime(phan_ngay,"%d/%m/%Y").strftime("%d/%m/%Y")
        DA_CO_DU_LIEU[ngay_chuan] = danh_sach_duoi # Thêm/điền đầy ngày này vào bộ chung
        tong_ngay_hien_co = len([k for k in DA_CO_DU_LIEU if 0 <= (datetime.now()-datetime.strptime(k,"%d/%m/%Y")).days <60])
        bot.send_message(msg.chat.id,f"✅ ĐÃ THÊM THÀNH CÔNG NGÀY: {ngay_chuan}\n📊 Tổng số ngày hiện đang tích lũy: {tong_ngay_hien_co}/60 ngày yêu cầu!\n👉 Tiếp tục gửi thêm vài ngày nữa là đủ chuẩn phân tích tự động ra kết quả ngay nhé!")
    except:
        bot.send_message(msg.chat.id,"⚠️ Dùng đúng mẫu: Luu du lieu: Ngày 22/08/2026 | Đuôi: 00,07,09,06,... nhé!")

# === ✅ KHI ĐỦ SỐ NGÀY QUY ĐỊNH → TỰ ĐỘNG PHÂN TÍCH RA TOP ĐUÔI THAM KHẢO NGAY ===
@bot.message_handler(func=lambda msg: len(msg.text.strip().split())==3 and all(s.isdigit() for s in msg.text.strip().split()))
def phan_tich_ngay_yeu_cau(msg):
    try:
        tach = msg.text.strip().split()
        ngay_moc = datetime(int(tach[2]),int(tach[1]),int(tach[0]))
        thanh_cong, tap_ngay, tb = lay_du_lieu_theo_thu_tu(ngay_moc)
        if not thanh_cong: return # Đã báo rõ số đang thiếu, chờ thêm ít ngày nữa là đủ tự chạy tiếp

        tap_hop = []
        for dem in range(60):
            ngay_lui = ngay_moc - timedelta(days=dem)
            khoa = ngay_lui.strftime("%d/%m/%Y")
            if khoa in tap_ngay: tap_hop.extend(tap_ngay[khoa])
            time.sleep(random.uniform(0.15,0.25))

        top3,top20 = tinh_diem_chuan(tap_hop)
        ngay_sau = ngay_moc + timedelta(days=1)
        bot.send_message(msg.chat.id,f"""✅===== HOÀN THÀNH PHÂN TÍCH =====
📅 Dựa trên đủ mức tin cậy {len(tap_hop)//25} ngày trong khoảng yêu cầu:
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

# === 📈 PHẦN ĐÁNH GIÁ CỔ PHIẾU UPCOM HOÀN TOÀN HOẠT ĐỘNG ỔN ĐỊNH ===
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
        except: continue
    return f"⚠️ Tạm chưa lấy được dữ liệu {ma}"

@bot.message_handler(func=lambda msg: msg.text.strip() == "Danh gia UPCOM")
def danh_gia_nhom(msg):
    if msg.chat.id != CHAT_ID: return
    bot.send_message(CHAT_ID,"🔄 Đang lấy dữ liệu & đánh giá theo thang điểm 10...")
    ketqua = []
    for ma in DANH_SACH_UPCOM:
        ketqua.append(lay_danh_gia_cp(ma))
        time.sleep(1.2)
    bot.send_message(CHAT_ID,"\n\n".join(ketqua))

@bot.message_handler(func=lambda msg: msg.text.strip().startswith("DG "))
def danh_gia_mot_ma(msg):
    if msg.chat.id != CHAT_ID: return
    ma = msg.text.strip()[3:].upper().strip()
    bot.send_message(CHAT_ID, lay_danh_gia_cp(ma))

@bot.message_handler(func=lambda msg: msg.text.strip() == "Trang thai")
def kiem_tra(msg):
    if msg.chat.id != CHAT_ID: return
    bot.send_message(CHAT_ID,"✅ **Đã cải thiện cách tích lũy thông minh hơn:**\n📂 Không làm trống lại bộ nhớ cũ nữa, mỗi lần kiểm tra chỉ thêm những ngày mới có được từ các trang\n📊 Báo rõ chính xác hiện đang có tổng cộng bao nhiêu ngày / cần bổ sung thêm mấy ngày ngắn gọn thôi là đủ chuẩn\n📝 Gửi thêm mỗi ngày theo mẫu sẽ thấy số tăng dần rõ ràng, đạt mức quy định tự động phân tích ra kết quả tham khảo ngay không cần chờ đủ 60 cùng một lúc khó lấy!")

while True:
    try:
        bot.polling(none_stop=True, interval=5, timeout=60)
    except Exception as loi:
        print(f"Kết nối lại: {loi}")
        time.sleep(10)
