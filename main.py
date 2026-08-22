# === BOT HOÀN CHỈNH: CỬA SỔ TRƯỢT ĐỦ 60 NGÀY + CÔNG THỨC CHUẨN CỐ ĐỊNH ===
import os
from flask import Flask
from threading import Thread
import time, telebot, requests
from collections import Counter
from datetime import datetime, timedelta

# === Giữ bot chạy liên tục ổn định ===
app = Flask(__name__)
@app.route('/')
def giu_song(): return "✅ Bot chuẩn: giữ đủ đúng 60 ngày gần nhất + công thức tính không đổi!"
def chay_server(): app.run(host="0.0.0.0", port=int(os.environ.get("PORT",8080)))
Thread(target=chay_server).start()

# === THÔNG TIN BOT ===
BOT_TOKEN = "8520938638:AAEHwQp89_P2slG7YTkod4z6_XvYbgBD7ns"
CHAT_ID = 7064473358
bot = telebot.TeleBot(BOT_TOKEN)

# === LƯU LỊCH SỬ CÙNG NGÀY RÕ RÀNG ĐỂ LỌC ĐỦ ĐÚNG 60 NGÀY ===
# Định dạng: {"ngay":"DD/MM/YYYY", "danh_sach_duoi": ["xx","xx",...]}
LICH_SU_DU_LIEU = []

# === ✅ CÔNG THỨC CHUẨN ĐÓNG CHỐT KHÔNG BAO GIỜ THAY ĐỔI ===
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
                khoang_cach.append(vitri[i]-vitri[i-1])
            chenh_lech = max(khoang_cach) - min(khoang_cach)
            do_deu = round(10/(1+chenh_lech),2)
            diem = round(so_lan * 4.0 + do_deu * 10.0, 2) # CỐ ĐỊNH HOÀN TOÀN
        ds_diem.append((-diem,ma,so_lan))
    ds_diem.sort()
    top3 = [(m,sl) for _,m,sl in ds_diem[:3]]
    top20 = [m for _,m,_ in ds_diem[:20]]
    return top3, top20

# === XỬ LÝ KHI BẠN CẬP NHẬT NGÀY MỚI: tự cắt lấy đủ đúng 60 ngày lùi về ===
@bot.message_handler(func=lambda msg: msg.text.startswith("NGAYMOC|"))
def xu_ly_ngay_moc(msg):
    if msg.chat.id != CHAT_ID: return
    try:
        _, ngay_moc_str, danh_sach_duoi_str = msg.text.split("|",2)
        ngay_moc = datetime.strptime(ngay_moc_str.strip(),"%d/%m/%Y")
        danh_sach_ngay = danh_sach_duoi_str.strip().split(",")

        # Thêm vào lịch sử đầy đủ
        LICH_SU_DU_LIEU.append({"ngay":ngay_moc_str.strip(), "ngay_dt":ngay_moc, "ds":danh_sach_ngay})

        # === LỌC CHÍNH XÁC NHỮNG NGÀY NẰM TRONG VÒNG 60 NGÀY LÙI TỪ NGÀY MỚI ===
        ngay_batdau = ngay_moc - timedelta(days=59) # đủ trọn 60 ngày liên tục
        ds_trong_60ngay = []
        for muc in LICH_SU_DU_LIEU:
            if muc["ngay_dt"] >= ngay_batdau and muc["ngay_dt"] <= ngay_moc:
                ds_trong_60ngay.extend(muc["ds"])

        # Tính theo công thức chuẩn cố định
        top3, top20 = tinh_diem_chuan(ds_trong_60ngay)

        nd = f"""🎯 PHÂN TÍCH ĐỦ CHÍNH XÁC 60 NGÀY: {ngay_batdau.strftime('%d/%m/%Y')} ➡ {ngay_moc_str.strip()}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Đủ {len(ds_trong_60ngay)} đuôi số trong khoảng thời gian yêu cầu
📌 Tiêu chí chuẩn không đổi: ưu tiên xuất hiện nhiều lần + khoảng cách lặp lại đều đặn nhất trong giai đoạn này!

🏆 TOP 3 ĐUÔI CÓ XÁC SUẤT QUY LUẬT CAO NHẤT ĐỂ THAM KHẢO TIẾP THEO:
1. 🥇 Đuôi {top3[0][0]} | Tổng xuất hiện {top3[0][1]} lần trong giai đoạn 60 ngày
2. 🥈 Đuôi {top3[1][0]} | Tổng xuất hiện {top3[1][1]} lần – tần suất cao & chu kỳ đều đặn tốt thứ hai
3. 🥉 Đuôi {top3[2][0]} | Tổng xuất hiện {top3[2][1]} lần – có quy luật lặp lại đáng tin cậy thứ ba

📋 Danh sách 20 đuôi có điểm tốt nhất tiếp theo:
▫️ {'  ▫️ '.join(top20)}

💡 Đã cắt bỏ tự động các ngày cũ hơn ngoài 60 ngày yêu cầu, không thay đổi một chút nào bộ công thức đánh giá đã thống nhất!
⚠️ Chỉ phân tích quy luật thống kê trong khoảng thời gian đã chọn, mang tính tham khảo vui chơi có trách nhiệm!
"""
        bot.send_message(CHAT_ID,nd)
    except Exception as e:
        bot.send_message(CHAT_ID,f"⚠️ Gửi đúng định dạng ví dụ: NGAYMOC|25/08/2026|13,00,83,32,84,22,83,49,36,94 nhé! Lỗi: {e}")

# === VẪN GIỮ NGUYÊN PHẦN CỔ PHIẾU UPCOM HOẠT ĐỘNG ĐỒNG BỘ ===
DANH_SACH_UPCOM = ["SHB","HDB","TCB","VPB","MBB","SSB","EIB","VIX","MBS","VCI","SSI","ACB","BID","VCB"]
API_KEY_ALPHA = ["SYHGO5Z8DE4RAU8E","52MWBOYE0RSLQE8E","N8TO30AM8DVVGDE7"]

def lay_du_lieu_co_phieu(ma):
    for apikey in API_KEY_ALPHA:
        try:
            url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={ma}.VN&apikey={apikey}&outputsize=compact"
            res = requests.get(url, timeout=10).json()
            if "Time Series" in res:
                ds_ngay = sorted(res["Time Series (Daily)"].items(), reverse=True)[:14]
                gia_dong = [float(v["4. close"]) for _, v in ds_ngay]
                if len(gia_dong)>=10:
                    ema5 = round(sum(gia_dong[:5])/5,2); ema10 = round(sum(gia_dong[:10])/10,2)
                    xu_huong = "📈 Xu hướng tăng tốt" if ema5>ema10 else "📉 Cần theo dõi chờ cải thiện"
                    diem = round(min(10,5+(ema5-ema10)*100/ema10),1)
                    gia_hien_tai = gia_dong[0]
                    chot_loi = round(gia_hien_tai*1.03,2); cat_lo = round(gia_hien_tai*0.97,2)
                    return f"{ma} | Điểm: {diem}/10 | {xu_huong}\nGiá hiện tại: {gia_hien_tai:,}\n🎯 Giá chốt lời đề xuất: {chot_loi:,}\n🛡️ Giá cắt lỗ an toàn: {cat_lo:,}"
        except: continue
    return f"⚠️ Tạm thời chưa lấy được dữ liệu {ma}, vui lòng thử lại sau chốc lát nhé!"

@bot.message_handler(func=lambda msg: msg.text.strip() == "Danh gia UPCOM")
def danh_gia_nhom_cp(msg):
    if msg.chat.id != CHAT_ID: return
    bot.send_message(CHAT_ID,"🔄 Đang lấy dữ liệu & đánh giá nhóm cổ phiếu theo thang điểm 10 rõ ràng...")
    ketqua=[]
    for ma in DANH_SACH_UPCOM:
        ketqua.append(lay_du_lieu_co_phieu(ma)); time.sleep(1.3)
    bot.send_message(CHAT_ID,"\n\n".join(ketqua))

@bot.message_handler(func=lambda msg: msg.text.strip().startswith("DG "))
def danh_gia_mot_ma(msg):
    if msg.chat.id != CHAT_ID: return
    ma = msg.text.strip()[3:].upper().strip()
    bot.send_message(CHAT_ID, lay_du_lieu_co_phieu(ma))

def bao_dinh_ky():
    while True:
        gio_vn = datetime.utcnow() + timedelta(hours=7)
        bot.send_message(CHAT_ID,f"✅ BÁO HOẠT ĐỘNG: {gio_vn.strftime('%H:%M %d/%m/%Y')} | Sẵn sàng nhận ngày mốc → tự lọc đủ đúng 60 ngày gần nhất & tính theo chuẩn đã thỏa thuận!")
        time.sleep(10800)
Thread(target=bao_dinh_ky, daemon=True).start()

@bot.message_handler(func=lambda msg: msg.text.strip() == "Trang thai")
def kiem_tra_nhanh(msg):
    if msg.chat.id != CHAT_ID: return
    bot.send_message(CHAT_ID,"✅ Đủ chức năng yêu cầu:\n📌 Nhận ngày mốc → tự lọc đủ đúng 60 ngày liên tục gần nhất kết thúc đúng ngày đó\n📌 Luôn áp dụng y hệt công thức chuẩn không thay đổi\n📌 Ghi rõ khoảng thời gian phân tích để đối chiếu dễ dàng\n📌 Lưu lịch sử đầy đủ từng ngày cập nhật\n📌 Lệnh dùng: NGAYMOC|ngày|danh sách đuôi | Danh gia UPCOM | DG mã | Trang thai")

while True:
    try: bot.polling(none_stop=True,interval=5,timeout=30)
    except Exception as loi: print(f"Xử lý tạm dừng ngắn: {loi}"); time.sleep(10)
