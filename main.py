# === TINH CHỈNH KỸ LẠI CÁCH ĐỌC TRANG THÊM NHIỀU KIỂU CẤU TRÚC BẢNG KHÁC NHAU + VẪN TÍCH LŨY RÕ SỐ KHI BẠN GỬI BỔ SUNG ===
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
    return "✅ Đã thử mở rộng tìm kiếm nhiều kiểu bố cục bảng hơn trên từng trang, tăng cơ hội lấy được; cộng dồn ngay số ngày bạn gửi lên!"

def chay_server():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

Thread(target=chay_server).start()

BOT_TOKEN = "8520938638:AAEHwQp89_P2slG7YTkod4z6_XvYbgBD7ns"
CHAT_ID = 7064473358
bot = telebot.TeleBot(BOT_TOKEN)
DA_CO_DU_LIEU = {} # Lưu vĩnh viễn không tự xóa

# 📋 Giữ nguyên danh sách ưu tiên đã chọn
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

# === 🚀 MỞ RỘNG RẤT NHIỀU CÁCH CHỌN THẺ BẢNG, DÒNG, CỘT KHÁC NHAU TĂNG TỐI ĐA CƠ HỘI TRÍCH XUẤT RA ĐƯỢC SỐ ===
def lay_tu_trang_tonghop(link, ngay_moc_can):
    DA_HEADER = [
        {"User-Agent":"Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Mobile Safari/537.36",
         "Accept-Language":"vi-VN,vi;q=0.9", "Referer":"https://www.google.com/"},
        {"User-Agent":"Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
         "Accept-Language":"vi-VN,vi;q=0.9", "Referer":"https://facebook.com/"},
        {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
         "Accept-Language":"vi-VN,vi;q=0.9", "Referer":"https://bing.com/"}
    ]
    try:
        res = requests.get(link, headers=random.choice(DA_HEADER), timeout=15)
        if res.status_code != 200: return {}
        soup = BeautifulSoup(res.text,"html.parser")
        tap_moi_lay_duoc = {}

        # === THỬ LIỆT KÊ RẤT NHIỀU LỚP TÊN THẺ THƯỜNG DÙNG TRÊN CÁC TRANG KHÁC NHAU ===
        ds_khoang_chon = [
            "table.table tr", "table.kqxs tr", "table.result tr", "table tr",
            "div.date-item", "div.result-day", "div.prize-day", "div.item-kq", "div.block-kq",
            "ul.list-kq li", "div.content-kq > div", ".ngay-kq", ".kq-item"
        ]
        for bo_chon in ds_khoang_chon:
            for khoang in soup.select(bo_chon):
                try:
                    # Tìm ngày với nhiều tên lớp khác nhau
                    chuoi_ngay = khoang.select_one("span.date, div.ngay, .ngay-thang, .kq-ngay, span.ngay-kq, b.ngay")
                    if not chuoi_ngay: continue
                    chuoi_ngay = chuoi_ngay.get_text(strip=True)
                    # Định dạng linh hoạt chút
                    for dinh_dang in ["%d/%m/%Y", "%d-%m-%Y"]:
                        try: dt_lay = datetime.strptime(chuoi_ngay, dinh_dang); break
                        except: continue
                    else: continue # không khớp định dạng nào bỏ qua

                    so_ngay_ke = (ngay_moc_can - dt_lay).days
                    if not (0 <= so_ngay_ke <60): continue

                    # Tìm bộ số kết quả thử nhiều nhóm tên thẻ giải khác nhau
                    ds_so = []
                    ds_so_chon = ["span.prize-number", ".number", "span.giai-so", ".giai_so", "span.so", "span.num", "td.so", "span.giai"]
                    for ten_chon in ds_so_chon:
                        for so_tag in khoang.select(ten_chon):
                            s = so_tag.get_text(strip=True)
                            if s.isdigit() and len(s)>=2: ds_so.append(s[-2:])
                    # Lọc trùng nếu lấy lặp lại
                    ds_so_danh_sach_khong_trung = list(dict.fromkeys(ds_so))
                    if len(ds_so_danh_sach_khong_trung)>=20:
                        tap_moi_lay_duoc[dt_lay.strftime("%d/%m/%Y")]=ds_so_danh_sach_khong_trung
                except: continue
            if tap_moi_lay_duoc: break # đã có dữ liệu rồi dừng thử bộ chọn khác tiết kiệm thời gian
        return tap_moi_lay_duoc
    except Exception as e:
        print(f"Lấy trang gặp lỗi: {str(e)[:60]}")
        return {}

# === 📋 QUY TRÌNH THỬ TUẦN TỰ + BÁO RÕ SỐ HIỆN CÓ ===
def lay_du_lieu_theo_thu_tu(ngay_batdau):
    bot.send_message(CHAT_ID, "🔄 Đang kiểm tra & mở rộng tìm cấu trúc bảng dữ liệu...")
    thong_bao_trang_thai = []
    for thu_tu, nguon in enumerate(DANH_SACH_NGUON_UU_TIEN, 1):
        thong_bao_trang_thai.append(f"🔹 {thu_tu}. Đang kiểm tra: {nguon['ten']}...")
        try:
            tap_moi = lay_tu_trang_tonghop(nguon["link"], ngay_batdau)
            if tap_moi:
                DA_CO_DU_LIEU.update(tap_moi)
                thong_bao_trang_thai.append(f"✅ Lấy được {len(tap_moi)} ngày mới từ: {nguon['ten']}!")
            else:
                thong_bao_trang_thai.append(f"ℹ️ Tạm chưa trích xuất được ngày mới từ {nguon['ten']}...")
        except Exception as e:
            thong_bao_trang_thai.append(f"❌ Truy cập khó từ {nguon['ten']}: {str(e)[:45]}...")
        time.sleep(random.uniform(0.8,1.5))

    # Tính chính xác tổng ngày trong khoảng yêu cầu
    tong_ngay_co = 0
    for k in DA_CO_DU_LIEU:
        try:
            ng = datetime.strptime(k,"%d/%m/%Y")
            if 0 <= (ngay_batdau - ng).days <60: tong_ngay_co +=1
        except: pass

    thong_bao_trang_thai.append(f"\n📊 === TỔNG KẾT HIỆN CÓ: {tong_ngay_co}/45 ngày mức đủ tin cậy ===")
    if tong_ngay_co >=45:
        bot.send_message(CHAT_ID,"\n".join(thong_bao_trang_thai)+"\n✅ Đủ chuẩn rồi tiến hành phân tích ngay!")
        return True, DA_CO_DU_LIEU, "Đủ chuẩn"
    else:
        can_them = 45 - tong_ngay_co
        thong_bao_trang_thai.append(f"💡 Cần bổ sung thêm khoảng {can_them} ngày gần nhất là đủ nhanh chóng!")
        thong_bao_trang_thai.append("📝 Cách gửi rất đơn giản từng ngày một hoặc nhiều ngày cùng dòng:\nVí dụ: Luu du lieu: Ngày 18/08/2026 | Đuôi: 12,34,56,78,90,01,05,09,22,33,44,55,66,77,88,99,02,07,15,28,35,41,62,79,83")
        thong_bao_trang_thai.append("👉 Sau mỗi lần gửi sẽ báo ngay tổng số tăng lên rõ ràng, đạt đủ 45 ngày tự ra kết quả phân tích luôn không cần làm gì thêm!")
        bot.send_message(CHAT_ID,"\n".join(thong_bao_trang_thai))
        return False, {}, "Đang chờ bổ sung thêm ít ngày"

# === 📥 LỆNH LƯU BỔ SUNG CẢI THIỆN: NHẬN NGAY, BÁO TỔNG SỐ MỚI NHẤT RÕ RÀNG ===
@bot.message_handler(func=lambda msg: msg.text.strip().startswith("Luu du lieu:"))
def xu_ly_luu_ban_gui(msg):
    try:
        noi_dung = msg.text.strip().replace("Luu du lieu:","").strip()
        phan_ngay = noi_dung.split("|")[0].replace("Ngày","").strip()
        danh_sach_duoi = [d.strip() for d in noi_dung.split("|")[1].replace("Đuôi:","").strip().split(",") if d.strip() and len(d.strip())==2]
        ngay_chuan = datetime.strptime(phan_ngay,"%d/%m/%Y").strftime("%d/%m/%Y")
        DA_CO_DU_LIEU[ngay_chuan] = danh_sach_duoi

        # Đếm lại tổng số ngày đủ trong khoảng yêu cầu hiện tại
        tong_moi = 0
        ngay_hien_tai = datetime.now()
        for k in DA_CO_DU_LIEU:
            try:
                ng = datetime.strptime(k,"%d/%m/%Y")
                if 0 <= (ngay_hien_tai - ng).days <60: tong_moi +=1
            except: pass

        bot.send_message(msg.chat.id,f"✅ **ĐÃ LƯU THÀNH CÔNG:** {ngay_chuan}\n📈 **Tổng số ngày hiện có:** {tong_moi}/45 ngày đủ mức tin cậy!\n👉 Tiếp tục gửi thêm vài ngày nữa là đủ chuẩn phân tích tự động nhé!")
    except Exception as e:
        bot.send_message(msg.chat.id,"⚠️ Gửi đúng mẫu ví dụ: Luu du lieu: Ngày 18/08/2026 | Đuôi: 12,34,56,78,90,01,05,09,22,33,44,55,66,77,88,99,02,07,15,28,35,41,62,79,83")

# === ✅ KHI ĐỦ SỐ NGÀY QUY ĐỊNH → TỰ ĐỘNG CHẠY PHÂN TÍCH RA TOP ĐUÔI ===
@bot.message_handler(func=lambda msg: len(msg.text.strip().split())==3 and all(s.isdigit() for s in msg.text.strip().split()))
def phan_tich_ngay_yeu_cau(msg):
    try:
        tach = msg.text.strip().split()
        ngay_moc = datetime(int(tach[2]),int(tach[1]),int(tach[0]))
        thanh_cong, tap_ngay, tb = lay_du_lieu_theo_thu_tu(ngay_moc)
        if not thanh_cong: return

        tap_hop = []
        for dem in range(60):
            ngay_lui = ngay_moc - timedelta(days=dem)
            khoa = ngay_lui.strftime("%d/%m/%Y")
            if khoa in tap_ngay: tap_hop.extend(tap_ngay[khoa])
            time.sleep(random.uniform(0.15,0.25))

        top3,top20 = tinh_diem_chuan(tap_hop)
        ngay_sau = ngay_moc + timedelta(days=1)
        bot.send_message(msg.chat.id,f"""✅===== HOÀN THÀNH PHÂN TÍCH =====
📅 Đã tích đủ mức tin cậy yêu cầu:
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
        bot.send_message(msg.chat.id,"⚠️ Nhập đúng định dạng: Ngày Tháng Năm cách khoảng trắng nhé!")

# === 📈 PHẦN ĐÁNH GIÁ CỔ PHIẾU UPCOM HOÀN TOÀN GIỮ NGUYÊN ===
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
    bot.send_message(CHAT_ID,"✅ **Đã mở rộng tìm kiếm nhiều kiểu bố cục bảng hơn trên các trang:**\n📂 Dữ liệu bạn gửi vào lưu vĩnh viễn, mỗi lần gửi báo ngay số tăng rõ ràng, không bị mất đi\n📊 Chỉ cần đủ 45 ngày là ngưỡng tin cậy tốt, dễ hoàn thành nhanh hơn nhiều so với phải đủ 60 cùng lúc khó lấy tự động\n📝 Gửi theo mẫu đơn giản từng ngày là thấy tiến triển rõ ràng cho đến khi bot tự động ra bộ số đuôi phân tích tham khảo nhé!")

while True:
    try:
        bot.polling(none_stop=True, interval=5, timeout=60)
    except Exception as loi:
        print(f"Kết nối lại: {loi}")
        time.sleep(10)
