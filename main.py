# === BOT CHÍNH XÁC: GỬI ẢNH → YÊU CẦU BẠN GHI 3 SỐ → NHẬN ĐÚNG NGÀY BẠN NÓI → PHÂN TÍCH + VẪN ĐỦ CỔ PHIẾU ===
import os
from flask import Flask
from threading import Thread
import time, telebot, requests
from collections import Counter
from datetime import datetime, timedelta

app = Flask(__name__)
@app.route('/')
def giu_song(): return "✅ Đã chỉnh: bạn ghi 3 số ngày/tháng/năm là nhận đúng ngay, không sai ngày nữa!"
def chay_server(): app.run(host="0.0.0.0", port=int(os.environ.get("PORT",8080)))
Thread(target=chay_server).start()

BOT_TOKEN = "8520938638:AAEHwQp89_P2slG7YTkod4z6_XvYbgBD7ns"
CHAT_ID = 7064473358
bot = telebot.TeleBot(BOT_TOKEN)

LICH_SU_XOSO = []
dang_cho_ngay = {} # Ghi nhớ đang chờ bạn trả số ngày
API_KEY_ALPHA = ["SYHGO5Z8DE4RAU8E","52MWBOYE0RSLQE8E","N8TO30AM8DVVGDE7"]
DANH_SACH_UPCOM = ["SHB","HDB","TCB","VPB","MBB","SSB","EIB","VIX","MBS","VCI","SSI","ACB","BID","VCB"]

# === Công thức tính điểm xổ số chuẩn ===
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
            chenh_lech = max(khoang_cach) - min(khoang_cach)
            do_deu = round(10 / (1 + chenh_lech), 2)
            diem = round(so_lan * 4.0 + do_deu * 10.0, 2)
        ds_diem.append((-diem, ma, so_lan))
    ds_diem.sort()
    top3 = [(m, sl) for _, m, sl in ds_diem[:3]]
    top20 = [m for _, m, _ in ds_diem[:20]]
    return top3, top20

# === 📸 Nhận ảnh → hỏi đúng ngắn gọn chờ bạn cho ngày chính xác ===
@bot.message_handler(content_types=['photo'])
def khi_nhan_anh(msg):
    if msg.chat.id != CHAT_ID: return
    dang_cho_ngay[msg.chat.id] = True
    bot.send_message(msg.chat.id,"📸 Đã nhận ảnh!\nVui lòng gửi: Ngày Tháng Năm")

# === ✅ Nhận đúng 3 số bạn gõ → chuyển định dạng, dùng chính xác ngày đó phân tích ===
@bot.message_handler(func=lambda msg: msg.chat.id == CHAT_ID and dang_cho_ngay.get(msg.chat.id)==True)
def xu_ly_ngay_ban_cho(msg):
    try:
        tach = msg.text.strip().split()
        if len(tach)!=3:
            bot.send_message(msg.chat.id,"⚠️ Chỉ ghi đủ 3 số cách khoảng trắng: VD: 21 08 2026 nhé!")
            return
        ngay_str = f"{tach[0]}/{tach[1]}/{tach[2]}"
        ngay_moc = datetime.strptime(ngay_str,"%d/%m/%Y")

        # 📌 Bạn cho ngày nào tôi sẽ bổ sung & dùng đúng bộ đuôi số của ngày đó cho bạn phân tích chính xác
        bot.send_message(msg.chat.id,f"✅ **ĐÃ NHẬN CHÍNH XÁC NGÀY: {ngay_str}** ✅")
        bot.send_message(msg.chat.id,"Vui lòng gửi tiếp danh sách đuôi số ngày này cách dấu phẩy nhé!")
        dang_cho_ngay[msg.chat.id] = False
        # Lưu tạm ngày vừa nhận chờ bạn gửi bộ số tương ứng
        bot.register_next_step_handler(msg, luu_danh_sach_duoi, ngay_moc)
    except:
        bot.send_message(msg.chat.id,"⚠️ Gõ đúng 3 số cách khoảng trắng là được nhé!")

def luu_danh_sach_duoi(msg, ngay_da_nhan):
    try:
        ds_duoi = [d.strip() for d in msg.text.strip().split(",") if d.strip()]
        LICH_SU_XOSO.append({"ngay_dt":ngay_da_nhan, "ds":ds_duoi})
        LICH_SU_XOSO.sort(key=lambda x:x["ngay_dt"])
        ngay_batdau = ngay_da_nhan - timedelta(days=59)
        ds_trong_60ngay = []
        for muc in LICH_SU_XOSO:
            if muc["ngay_dt"] >= ngay_batdau and muc["ngay_dt"] <= ngay_da_nhan:
                ds_trong_60ngay.extend(muc["ds"])
        top3, top20 = tinh_diem_chuan(ds_trong_60ngay)
        bot.send_message(msg.chat.id,"✅ **ĐANG PHÂN TÍCH XONG!** ✅")
        nd = f"""🎯 KẾT QUẢ: {ngay_batdau.strftime('%d/%m/%Y')} ➡ {ngay_da_nhan.strftime('%d/%m/%Y')}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏆 TOP 3 ĐUÔI:
1. 🥇 Đuôi {top3[0][0]} – xuất hiện {top3[0][1]} lần | tần suất cao + đều đặn nhất
2. 🥈 Đuôi {top3[1][0]} – xuất hiện {top3[1][1]} lần – tốt thứ hai
3. 🥉 Đuôi {top3[2][0]} – xuất hiện {top3[2][1]} lần – đáng tin cậy thứ ba

📋 DANH SÁCH MỞ RỘNG:
▫️ {'  ▫️ '.join(top20)}
⚠️ Chỉ tham khảo vui chơi có trách nhiệm!
"""
        bot.send_message(msg.chat.id,nd)
    except:
        bot.send_message(msg.chat.id,"⚠️ Gửi danh sách đuôi cách dấu phẩy đúng nhé!")

# === 📈 PHẦN CỔ PHIẾU UPCOM NGUYÊN VẸN HOẠT ĐỘNG ===
def lay_danh_gia_cp(ma):
    for apikey in API_KEY_ALPHA:
        try:
            url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={ma}.VN&apikey={apikey}&outputsize=compact"
            res = requests.get(url, timeout=12).json()
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
def kiem_tra_chung(msg):
    if msg.chat.id != CHAT_ID: return
    bot.send_message(CHAT_ID,"✅ **ĐỦ HOÀN HẢO:**\n📸 Xổ số: gửi ảnh → ghi Ngày Tháng Năm theo đúng bạn biết chính xác nhất → phân tích đủ 60 ngày đúng ngày đó\n📈 Cổ phiếu: lệnh *Danh gia UPCOM* / *DG MãCP* vẫn trả đủ điểm, giá, chốt lời như yêu cầu trước đó\n📌 Không còn đọc sai ngày tự động nữa, bạn cho ngày nào dùng đúng ngày đó!")

while True:
    try: bot.polling(none_stop=True, interval=5, timeout=60)
    except Exception as loi: print(f"Kết nối lại: {loi}"); time.sleep(10)
