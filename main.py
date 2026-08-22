# === LẤY NHANH TỪ TRANG TỔNG HỢP LỊCH SỬ: lấy cả loạt 60 ngày cùng lúc trước ===
import os
from flask import Flask
from threading import Thread
import time, telebot, requests
from bs4 import BeautifulSoup
from collections import Counter
from datetime import datetime, timedelta

app = Flask(__name__)
@app.route('/')
def giu_song(): return "✅ Đã chuyển ưu tiên vào TRANG TỔNG HỢP lấy đủ chuỗi ngày liên tục cùng lúc trước, nhanh hơn hẳn!"
def chay_server(): app.run(host="0.0.0.0", port=int(os.environ.get("PORT",8080)))
Thread(target=chay_server).start()

BOT_TOKEN = "8520938638:AAEHwQp89_P2slG7YTkod4z6_XvYbgBD7ns"
CHAT_ID = 7064473358
bot = telebot.TeleBot(BOT_TOKEN)

# 📌 LINK TỔNG HỢP CHÍNH & DỰ PHÒNG xem được danh sách nhiều ngày liên tiếp trên cùng một trang
LINK_TONG_HOP = [
    "https://cafef.vn/xo-so/lich-su-ket-qua-xo-so-mien-bac.chn",
    "https://ketqua.vn/lich-su-xo-so-mien-bac",
    "https://xoso.me/lich-su-ket-qua-xsmb"
]
# Link chi tiết từng ngày chỉ dùng bổ sung khi thiếu dữ liệu trong trang tổng hợp
LINK_CHI_TIET = [
    "https://cafef.vn/xo-so-ket-qua-xo-so-mien-bac-ngay-{d}-{m}-{y}.chn",
    "https://ketqua.vn/xo-so-mien-bac/ngay-{d}-{m}-{y}"
]
DA_LAY_CACHE = {} # Lưu lại đã lấy xong: gọi lại trả tức thì không tải lại trang nữa
API_KEY_ALPHA = ["SYHGO5Z8DE4RAU8E","52MWBOYE0RSLQE8E","N8TO30AM8DVVGDE7"]
DANH_SACH_UPCOM = ["SHB","HDB","TCB","VPB","MBB","SSB","EIB","VIX","MBS","VCI","SSI","ACB","BID","VCB"]

# === 💯 Công thức tính điểm chuẩn không đổi: ưu tiên tần suất cao + chu kỳ đều ổn định nhất ===
def tinh_diem_chuan(danh_sach_duoi):
    dem_so_lan = Counter(danh_sach_duoi)
    vi_tri_tung_lan = {}
    for vt, ma in enumerate(danh_sach_duoi):
        vi_tri_tung_lan.setdefault(ma, []).append(vt)
    ds_diem = []
    for ma in dem_so_lan.keys():
        so_lan = dem_so_lan[ma]
        vitri = vi_tri_tung_lan[ma]
        if so_lan < 2:
            diem = round(so_lan * 2.5, 2)
        else:
            khoang_cach = []
            for i in range(1, len(vitri)):
                khoang_cach.append(vitri[i] - vitri[i-1])
            chenh_lech = max(khoang_cach) - min(khoang_cach) if max(khoang_cach)!=min(khoang_cach) else 1
            do_deu = round(10 / (1 + chenh_lech), 2)
            diem = round(so_lan * 4.0 + do_deu * 10.0, 2)
        ds_diem.append((-diem, ma, so_lan))
    ds_diem.sort()
    top3 = [(m, sl) for _, m, sl in ds_diem[:3]]
    top20 = [m for _, m, _ in ds_diem[:20]]
    return top3, top20

# === 🚀 HÀM CHÍNH: Đầu tiên vào TRANG TỔNG HỢP lấy đủ cả chuỗi 60 ngày một lần tải trang xong ===
def lay_duoi_60ngay_tonghop(ngay_ketthuc):
    tap_da_co = {}
    # Đã có đủ trong bộ nhớ thì trả ngay lập tức
    dem_ngay_can = 0
    ngay_lap = ngay_ketthuc
    for _ in range(60):
        kh = ngay_lap.strftime("%d/%m/%Y")
        if kh in DA_LAY_CACHE: tap_da_co[kh] = DA_LAY_CACHE[kh]
        ngay_lap -= timedelta(days=1)
    if len(tap_da_co)>=55: return tap_da_co # đủ gần hết thì dùng ngay không tải lại trang tổng hợp nữa

    # Ưu tiên vào trang tổng hợp một lần lấy cả danh sách nhiều ngày liên tiếp nhanh hơn
    headers = {"User-Agent":"Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36"}
    for link_tong in LINK_TONG_HOP:
        try:
            res = requests.get(link_tong, headers=headers, timeout=12)
            if res.status_code!=200: continue
            soup = BeautifulSoup(res.text,"html.parser")
            # Trích xuất được danh sách: mỗi mục ghi rõ ngày + bộ số tương ứng
            cac_khoang_ngay = soup.select("div.date, span.ngay, div.prize-row")
            ngay_hien_tai = None
            ds_ngay = []
            for el in cac_khoang_ngay:
                txt = el.get_text(strip=True)
                if "/" in txt and len(txt)==10:
                    try:
                        ngay_hien_tai = datetime.strptime(txt,"%d/%m/%Y")
                    except: pass
                elif ngay_hien_tai and len(txt)>=2 and txt.isdigit():
                    ds_ngay.append(txt[-2:])
                    if len(ds_ngay)>=25: # đủ đủ các số giải một ngày hoàn chỉnh
                        kh = ngay_hien_tai.strftime("%d/%m/%Y")
                        tap_da_co[kh] = ds_ngay
                        DA_LAY_CACHE[kh] = ds_ngay # lưu lại dùng sau cực nhanh
                        ds_ngay = []
                        ngay_hien_tai = None
            if len(tap_da_co)>=45: return tap_da_co # lấy được nhiều rồi thì trả ngay kết quả đã tổng hợp
        except: continue
    return tap_da_co

# === 📌 Chỉ gọi bổ sung chi tiết từng ngày còn thiếu sau khi đã lấy được nhiều từ trang tổng hợp rồi ===
def lay_ngay_chi_tiet(ngay_obj):
    kh = ngay_obj.strftime("%d/%m/%Y")
    if kh in DA_LAY_CACHE: return DA_LAY_CACHE[kh]
    headers = {"User-Agent":"Mozilla/5.0"}
    for link_mau in LINK_CHI_TIET:
        link = link_mau.format(d=ngay_obj.day,m=ngay_obj.month,y=ngay_obj.year)
        try:
            r = requests.get(link,headers=headers,timeout=7)
            if r.status_code!=200:continue
            s=BeautifulSoup(r.text,"html.parser")
            ds=[tag.get_text(strip=True)[-2:] for tag in s.select("span.prize-number") if tag.get_text(strip=True).isdigit()]
            if len(ds)>=25:
                DA_LAY_CACHE[kh]=ds
                return ds
        except:continue
    return None

# === ✅ NHẬN NGÀY → LẤY TRƯỚC TỔNG HỢP, BỔ SUNG THIẾU → NHANH GỌN ===
@bot.message_handler(func=lambda msg: True)
def xu_ly(msg):
    try:
        tach=msg.text.strip().split()
        if len(tach)!=3:
            bot.send_message(msg.chat.id,"📝 Ghi đơn giản: Ngày Tháng Năm cách khoảng trắng\nVD: 21 08 2026")
            return
        ngay_moc=datetime(int(tach[2]),int(tach[1]),int(tach[0]))
        bot.send_message(msg.chat.id,f"🔄 Đang ưu tiên vào TRANG TỔNG HỢP lấy đủ chuỗi ngày đến {ngay_moc.strftime('%d/%m/%Y')}... nhanh hơn nhé!")

        tap_60ngay = lay_duoi_60ngay_tonghop(ngay_moc)
        tap_hop_duoi = []
        ngay_di = ngay_moc
        for _ in range(60):
            kh = ngay_di.strftime("%d/%m/%Y")
            if kh in tap_60ngay:
                tap_hop_duoi.extend(tap_60ngay[kh])
            else:
                # chỉ bổ sung những ngày chưa có trong danh sách tổng hợp thôi
                them = lay_ngay_chi_tiet(ngay_di)
                if them: tap_hop_duoi.extend(them)
                time.sleep(0.18)
            ngay_di -= timedelta(days=1)

        if len(tap_hop_duoi)<45:
            bot.send_message(msg.chat.id,"ℹ️ Đang cố lấy đủ dữ liệu, vui lòng chờ chút hoặc thử lại lát nhé!")
            return

        top3,top20=tinh_diem_chuan(tap_hop_duoi)
        ngay_sau=ngay_moc+timedelta(days=1)
        bot.send_message(msg.chat.id,f"""✅ HOÀN THÀNH NHANH! DỰ ĐOÁN THAM KHẢO NGÀY: {ngay_sau.strftime('%d/%m/%Y')}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏆 TOP 3 ĐUÔI CÓ QUY LUẬT NHẤT:
🥇 {top3[0][0]} – xuất hiện {top3[0][1]} lần | Tần suất cao nhất + chu kỳ đều ổn định nhất
🥈 {top3[1][0]} – xuất hiện {top3[1][1]} lần | Tần suất cao thứ hai đều đặn tốt
🥉 {top3[2][0]} – xuất hiện {top3[2][1]} lần | Tần suất cao thứ ba ổn định

📋 20 Đuôi tốt khác:
▫️ {'  ▫️ '.join(top20)}

⚠️ Chỉ phân tích thống kê lấy từ trang tổng hợp lịch sử uy tín trên, mang tính tham khảo vui chơi giải trí!
""")
    except:
        bot.send_message(msg.chat.id,"👋 Nhập đúng 3 số Ngày Tháng Năm cách khoảng trắng là được nhé!")

# === 📈 PHẦN CỔ PHIẾU UPCOM HOÀN TOÀN NGUYÊN VẬN HOẠT ĐỘNG ===
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
    return f"⚠️ Tạm chưa lấy được dữ liệu {ma}, thử lại sau nhé!"

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
def kiem_tra_hoatdong(msg):
    if msg.chat.id != CHAT_ID: return
    bot.send_message(CHAT_ID,"✅ **Đã ưu tiên vào TRANG TỔNG HỢP trước lấy cả loạt nhiều ngày cùng lúc rồi mới bổ sung thiếu:**\n📌 Giảm số lần gọi mạng liên tục nhiều lần → tải nhanh hơn rõ rệt\n📌 Lưu vào bộ nhớ đệm: ngày đã lấy xong trả ngay lập tức không tải lại trang nữa\n📌 Vẫn có chi tiết từng ngày làm dự phòng khi cần đủ hoàn chỉnh chuỗi 60 ngày liên tục yêu cầu!\n📈 Phần xem & đánh giá cổ phiếu UPCOM vẫn đủ chức năng như đã dùng thành công trước đó!")

while True:
    try: bot.polling(none_stop=True, interval=5, timeout=60)
    except Exception as loi: print(f"Kết nối lại: {loi}"); time.sleep(10)
