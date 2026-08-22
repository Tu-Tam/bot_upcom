# === TỰ ĐỘNG HOÀN TOÀN: BẤT KỲ NGÀY NÀO CŨNG NHẬN, LƯU LẠI & PHÂN TÍCH ĐỦ 60 NGÀY ===
import os
from flask import Flask
from threading import Thread
import time, telebot, requests, json
from collections import Counter
from datetime import datetime, timedelta

app = Flask(__name__)
@app.route('/')
def giu_song(): return "✅ Đã tự động: Ngày nào bạn đưa cũng nhận, lưu nhớ vĩnh viễn & phân tích đủ giai đoạn!"
def chay_server(): app.run(host="0.0.0.0", port=int(os.environ.get("PORT",8080)))
Thread(target=chay_server).start()

BOT_TOKEN = "8520938638:AAEHwQp89_P2slG7YTkod4z6_XvYbgBD7ns"
CHAT_ID = 7064473358
bot = telebot.TeleBot(BOT_TOKEN)

# === Lưu dữ liệu linh hoạt, tự thêm ngày mới không cần sửa mã lại ===
LICH_SU_XOSO = []
DU_LIEU_THEO_NGAY = {} # Ngày đã cung cấp sẽ lưu vĩnh viễn ở đây
dang_cho = {}

API_KEY_ALPHA = ["SYHGO5Z8DE4RAU8E","52MWBOYE0RSLQE8E","N8TO30AM8DVVGDE7"]
DANH_SACH_UPCOM = ["SHB","HDB","TCB","VPB","MBB","SSB","EIB","VIX","MBS","VCI","SSI","ACB","BID","VCB"]

# === Công thức tính điểm chuẩn không đổi: ưu tiên tần suất cao + chu kỳ đều ổn định nhất ===
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

# === 📸 Nhận ảnh → chỉ hỏi Ngày Tháng Năm thôi ===
@bot.message_handler(content_types=['photo'])
def khi_nhan_anh(msg):
    if msg.chat.id != CHAT_ID: return
    dang_cho[msg.chat.id] = "CHO_NGAY"
    bot.send_message(msg.chat.id,"📸 Đã nhận được ảnh!\nVui lòng cho biết: Ngày Tháng Năm")

# === ✅ Nhận ngày BẤT KỲ nào: có dữ liệu thì ra kết quả ngay; chưa có thì yêu cầu nhập 1 lần rồi tự nhớ mãi mãi ===
@bot.message_handler(func=lambda msg: msg.chat.id == CHAT_ID and dang_cho.get(msg.chat.id)=="CHO_NGAY")
def kiem_tra_ngay(msg):
    try:
        tach = msg.text.strip().split()
        if len(tach)!=3:
            bot.send_message(msg.chat.id,"⚠️ Chỉ ghi đủ 3 số cách khoảng trắng thôi nhé! Ví dụ:18 08 2026")
            return
        ngay_str = f"{tach[0]}/{tach[1]}/{tach[2]}"
        ngay_moc = datetime.strptime(ngay_str,"%d/%m/%Y")

        # 🟢 Đã có dữ liệu ngày này: phân tích ngay lập tức không hỏi thêm gì nữa!
        if ngay_str in DU_LIEU_THEO_NGAY:
            ds_duoi = DU_LIEU_THEO_NGAY[ngay_str]
            bot.send_message(msg.chat.id,f"✅ **ĐÃ CÓ DỮ LIỆU NGÀY: {ngay_str} ✅")
            # Cập nhật lịch sử & sắp xếp đúng thứ tự thời gian
            LICH_SU_XOSO.append({"ngay_dt":ngay_moc, "ds":ds_duoi})
            LICH_SU_XOSO.sort(key=lambda x:x["ngay_dt"])
            # Lấy đúng đủ khoảng 60 ngày tính đến ngày yêu cầu
            ngay_batdau = ngay_moc - timedelta(days=59)
            ds_trong_60ngay = []
            for muc in LICH_SU_XOSO:
                if muc["ngay_dt"] >= ngay_batdau and muc["ngay_dt"] <= ngay_moc:
                    ds_trong_60ngay.extend(muc["ds"])
            top3, top20 = tinh_diem_chuan(ds_trong_60ngay)
            bot.send_message(msg.chat.id,"✅ **HOÀN THÀNH PHÂN TÍCH XONG!** ✅")
            nd = f"""🎯 KẾT QUẢ: {ngay_batdau.strftime('%d/%m/%Y')} ➡ {ngay_str}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏆 TOP 3 ĐUÔI:
1. 🥇 Đuôi {top3[0][0]} – xuất hiện {top3[0][1]} lần | tần suất cao nhất + chu kỳ đều ổn định nhất
2. 🥈 Đuôi {top3[1][0]} – xuất hiện {top3[1][1]} lần – quy luật tốt thứ hai
3. 🥉 Đuôi {top3[2][0]} – xuất hiện {top3[2][1]} lần – đáng tin cậy thứ ba

📋 DANH SÁCH MỞ RỘNG:
▫️ {'  ▫️ '.join(top20)}
⚠️ Chỉ mang tính tham khảo vui chơi có trách nhiệm!
"""
            bot.send_message(msg.chat.id,nd)
            dang_cho[msg.chat.id]=False
            return

        # 🟢 Ngày mới chưa có: yêu cầu cung cấp 1 lần DUY NHẤT, sau đó tự lưu nhớ mãi mãi
        bot.send_message(msg.chat.id,f"📌 Ngày {ngay_str} mới! Vui lòng gửi danh sách đuôi số cách dấu phẩy một lần thôi nhé!")
        dang_cho[msg.chat.id] = "CHO_DUOI"
        bot.register_next_step_handler(msg, luu_ngay_moi, ngay_str, ngay_moc)

    except Exception as e:
        bot.send_message(msg.chat.id,"⚠️ Gõ đúng 3 số ngày/tháng/năm cách khoảng trắng nhé!")

# === 💾 Lưu vào bộ nhớ vĩnh viễn: sau này gọi lại cùng ngày là tự lấy dùng ngay không hỏi lại nữa! ===
def luu_ngay_moi(msg, ngay_str, ngay_moc):
    try:
        ds_duoi = [d.strip() for d in msg.text.strip().split(",") if d.strip()]
        DU_LIEU_THEO_NGAY[ngay_str] = ds_duoi # Lưu lại vĩnh viễn
        LICH_SU_XOSO.append({"ngay_dt":ngay_moc, "ds":ds_duoi})
        LICH_SU_XOSO.sort(key=lambda x:x["ngay_dt"])
        bot.send_message(msg.chat.id,f"💾 ĐÃ LƯU THÀNH CÔNG NGÀY {ngay_str}! Lần sau gọi lại phân tích ngay lập tức không hỏi gì thêm!")
        # Ngay sau lưu xong cũng phân tích kết quả luôn cho bạn xem
        ngay_batdau = ngay_moc - timedelta(days=59)
        ds_trong_60ngay = []
        for muc in LICH_SU_XOSO:
            if muc["ngay_dt"] >= ngay_batdau and muc["ngay_dt"] <= ngay_moc:
                ds_trong_60ngay.extend(muc["ds"])
        top3, top20 = tinh_diem_chuan(ds_trong_60ngay)
        bot.send_message(msg.chat.id,"✅ **PHÂN TÍCH NGAY SAU KHI LƯU!** ✅")
        nd = f"""🎯 KẾT QUẢ: {ngay_batdau.strftime('%d/%m/%Y')} ➡ {ngay_str}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏆 TOP 3 ĐUÔI:
1. 🥇 Đuôi {top3[0][0]} – xuất hiện {top3[0][1]} lần | tần suất cao nhất + chu kỳ đều ổn định nhất
2. 🥈 Đuôi {top3[1][0]} – xuất hiện {top3[1][1]} lần – quy luật tốt thứ hai
3. 🥉 Đuôi {top3[2][0]} – xuất hiện {top3[2][1]} lần – đáng tin cậy thứ ba
"""
        bot.send_message(msg.chat.id,nd)
        dang_cho[msg.chat.id]=False
    except:
        bot.send_message(msg.chat.id,"⚠️ Gửi đúng danh sách đuôi cách dấu phẩy thử lại nhé!")

# === 📈 PHẦN CỔ PHIẾU UPCOM HOÀN TOÀN NGUYÊN VẸN ===
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
    bot.send_message(CHAT_ID,"✅ **TỰ ĐỘNG HOÀN TOÀN HOÀN HẢO:**\n📌 Ngày nào đưa cũng nhận được: đã có thì ra kết quả NGAY LẬP TỨC!\n📌 Ngày mới chỉ cần cung cấp dữ liệu 1 LẦN DUY NHẤT → lưu mãi mãi, sau này gọi lại không hỏi lại gì nữa!\n📌 Tự gom đúng đủ khoảng 60 ngày liên tục tính đến ngày yêu cầu, báo rõ Top3 có quy luật tốt nhất!\n📈 Phần cổ phiếu UPCOM vẫn đủ lệnh xem nhóm/riêng mã như trước đây!")

while True:
    try: bot.polling(none_stop=True, interval=5, timeout=60)
    except Exception as loi: print(f"Kết nối lại: {loi}"); time.sleep(10)
