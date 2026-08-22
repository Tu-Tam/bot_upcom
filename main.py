# === CẢI THIỆN CHỐNG BỊ CHẶN: giống trình duyệt thật + thử lại + tự chuyển nguồn khi lỗi ===
import os
from flask import Flask
from threading import Thread
import time, telebot, requests
from bs4 import BeautifulSoup
from collections import Counter
from datetime import datetime, timedelta

app = Flask(__name__)
@app.route('/')
def giu_song(): return "✅ Đã nâng cấp: truy cập giống người dùng thật, thử lại nhẹ, chuyển nguồn tự động khi gặp khó lấy dữ liệu!"
def chay_server(): app.run(host="0.0.0.0", port=int(os.environ.get("PORT",8080)))
Thread(target=chay_server).start()

BOT_TOKEN = "8520938638:AAEHwQp89_P2slG7YTkod4z6_XvYbgBD7ns"
CHAT_ID = 7064473358
bot = telebot.TeleBot(BOT_TOKEN)

# 📌 Nguồn ưu tiên đã kiểm tra dễ truy cập, ít chặn nhất
LINK_TONG_HOP = [
    "https://ketqua.vn/lich-su-xo-so-mien-bac",
    "https://xoso.com.vn/lich-su-xo-so-mien-bac",
    "https://xsmb.ngaynay.net/lich-su"
]
DA_LAY_CACHE = {}

# === Giữ nguyên công thức tính điểm chuẩn đã thống nhất ===
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

# === 🛡️ Truy cập an toàn: giả danh trình duyệt thật, thử lại 2 lần nhẹ trước khi bỏ qua chuyển trang khác ===
def lay_tu_nguon(link):
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 14; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36",
        "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    for lan_thu in range(2):
        try:
            res = requests.get(link, headers=headers, timeout=10)
            if res.status_code == 200:
                return BeautifulSoup(res.text, "html.parser")
        except:
            time.sleep(0.6) # chờ nhẹ rồi thử lại một lần nữa
            continue
    return None

# === 📥 Trích xuất dữ liệu linh hoạt, kiểm tra đủ số giải mới chấp nhận ===
def lay_danh_sach_ngay(ngay_can_lay):
    khoa_ngay = ngay_can_lay.strftime("%d/%m/%Y")
    if khoa_ngay in DA_LAY_CACHE:
        return DA_LAY_CACHE[khoa_ngay]

    for link_tong in LINK_TONG_HOP:
        soup = lay_tu_nguon(link_tong)
        if not soup: continue
        # Cách đọc linh hoạt nhiều kiểu cấu trúc phổ biến
        cac_khoang = soup.select("table.table tr, div.item-result, div.prize-day, div.date-row")
        for khoang in cac_khoang:
            try:
                chuoi_ngay = khoang.select_one("span.date, div.ngay-thang").get_text(strip=True)
                dt_lay = datetime.strptime(chuoi_ngay, "%d/%m/%Y")
                if dt_lay != ngay_can_lay: continue
                cac_so = khoang.select("span.number, span.prize-number")
                ds_duoi = [s.get_text(strip=True)[-2:] for s in cac_so if s.get_text(strip=True).isdigit() and len(s.get_text(strip=True))>=2]
                if len(ds_duoi)>=25:
                    DA_LAY_CACHE[khoa_ngay] = ds_duoi
                    return ds_duoi
            except: continue
    return None

# === ✅ Nhận ngày → chạy an toàn, báo rõ đang lấy từ nguồn nào nếu cần ===
@bot.message_handler(func=lambda msg: True)
def xu_ly_ngay(msg):
    try:
        tach = msg.text.strip().split()
        if len(tach)!=3:
            bot.send_message(msg.chat.id,"📝 Nhập: Ngày Tháng Năm\nVD: 21 08 2026")
            return
        ngay_moc = datetime(int(tach[2]),int(tach[1]),int(tach[0]))
        bot.send_message(msg.chat.id,"🔄 Đang truy cập theo chế độ an toàn, thử lần lượt nguồn ổn định nhất... chờ chút nhé!")

        tap_hop = []
        for lui in range(60):
            ngay_lui = ngay_moc - timedelta(days=lui)
            kq = lay_danh_sach_ngay(ngay_lui)
            if kq: tap_hop.extend(kq)
            time.sleep(0.25) # khoảng chờ đủ an toàn không bị xem là tấn công

        if len(tap_hop)<45:
            bot.send_message(msg.chat.id,"ℹ️ Hiện tại kết nối lấy chưa đủ, bạn có thể hỗ trợ gửi 1 lần kết quả ngày gần nhất khi mở được trang xem được không? Tôi bổ sung tạm để phân tích tiếp ngay nhé!")
            return

        top3,top20 = tinh_diem_chuan(tap_hop)
        ngay_sau = ngay_moc + timedelta(days=1)
        bot.send_message(msg.chat.id,f"""✅ HOÀN THÀNH PHÂN TÍCH! DỰ ĐOÁN NGÀY: {ngay_sau.strftime('%d/%m/%Y')}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏆 TOP 3 ĐUÔI CÓ QUY LUẬT NHẤT:
🥇 {top3[0][0]} – xuất hiện {top3[0][1]} lần | Tần suất cao nhất + chu kỳ đều ổn định nhất
🥈 {top3[1][0]} – xuất hiện {top3[1][1]} lần
🥉 {top3[2][0]} – xuất hiện {top3[2][1]} lần

📋 Các đuôi tốt khác:
▫️ {'  ▫️ '.join(top20)}

⚠️ Chỉ mang tính tham khảo vui chơi giải trí!
""")
    except:
        bot.send_message(msg.chat.id,"👋 Nhập đúng 3 số Ngày Tháng Năm cách khoảng trắng là được nhé!")

# === Phần cổ phiếu UPCOM giữ nguyên hoàn chỉnh ===
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
    bot.send_message(CHAT_ID,"🔄 Đánh giá đang xử lý...")
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

while True:
    try: bot.polling(none_stop=True, interval=5, timeout=60)
    except Exception as loi: print(f"Kết nối lại: {loi}"); time.sleep(10)
