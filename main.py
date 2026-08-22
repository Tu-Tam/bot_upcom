# === BOT SỬA CHÍNH XÁC: MỖI NGÀY KHÁC NHAU LƯU DỮ LIỆU RIÊNG → RA KẾT QUẢ KHÁC BIỆT ===
import os
from flask import Flask
from threading import Thread
import time, telebot
from collections import Counter
from datetime import datetime, timedelta

app = Flask(__name__)
@app.route('/')
def giu_song(): return "✅ Đã sửa: mỗi ngày nhập mới đưa dữ liệu riêng → phân tích riêng → kết quả khác nhau đúng mong muốn!"
def chay_server(): app.run(host="0.0.0.0", port=int(os.environ.get("PORT",8080)))
Thread(target=chay_server).start()

BOT_TOKEN = "8520938638:AAEHwQp89_P2slG7YTkod4z6_XvYbgBD7ns"
CHAT_ID = 7064473358
bot = telebot.TeleBot(BOT_TOKEN)

LICH_SU_DU_LIEU = [] # Lưu rõ: mỗi phần là {"ngay_dt":ngay, "ds":danh_sach_duoi_ngay_do}
dang_cho = {}
danh_sach_cho_ngay = {} # Lưu tạm bộ đuôi số tương ứng từng ngày bạn cung cấp

# === 💯 VẪN GIỮ NGUYÊN HOÀN TOÀN CÔNG THỨC TÍNH ĐIỂM CHUẨN ĐÃ THỐNG NHẤT ===
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

# === 📸 Nhận ảnh → hỏi đúng câu, sau đó bạn sẽ gửi kèm bộ số đuôi tương ứng ngày đó ===
@bot.message_handler(content_types=['photo'])
def xu_ly_anh(msg):
    if msg.chat.id != CHAT_ID: return
    dang_cho[msg.chat.id] = "NGAY"
    bot.send_message(msg.chat.id,"📸 Đã nhận được ảnh!\nVui lòng ghi: Ngày lịch giáo tháng lịch giáo năm")

# === ✅ Nhận số ngày → yêu cầu thêm bộ đuôi số của đúng ngày đó để lưu riêng biệt không trộn lẫn ===
@bot.message_handler(func=lambda msg: msg.chat.id == CHAT_ID and dang_cho.get(msg.chat.id)=="NGAY")
def nhan_ngay(msg):
    try:
        tach = msg.text.strip().split()
        if len(tach)!=3:
            bot.send_message(msg.chat.id,"⚠️ Viết đủ 3 số cách khoảng trắng: VD:21 08 2026 nhé!")
            return
        ngay_str = f"{tach[0]}/{tach[1]}/{tach[2]}"
        ngay_moc = datetime.strptime(ngay_str,"%d/%m/%Y")
        dang_cho[msg.chat.id] = "DUOI"
        danh_sach_cho_ngay[msg.chat.id] = ngay_moc
        bot.send_message(msg.chat.id,f"✅ Đã ghi nhận ngày: {ngay_str}\nTiếp theo gửi đủ danh sách đuôi số cách dấu phẩy nhé!")
    except: bot.send_message(msg.chat.id,"⚠️ Sai định dạng! Thử lại: 21 08 2026")

# === ✅ Nhận đúng bộ đuôi số riêng của ngày vừa nhập → lưu vào lịch sử riêng biệt → tính cửa sổ trượt đúng thời điểm đó ===
@bot.message_handler(func=lambda msg: msg.chat.id == CHAT_ID and dang_cho.get(msg.chat.id)=="DUOI")
def nhan_ds_duoi(msg):
    try:
        ds_duoi = [d.strip() for d in msg.text.strip().split(",") if d.strip()]
        ngay_da_ghi = danh_sach_cho_ngay[msg.chat.id]

        # 🟢 LƯU RIÊNG MỘT MỤC DỊCH VỤ NGÀY NÀY → KHÔNG TRỘN VỚI DỮ LIỆU KHÁC
        LICH_SU_DU_LIEU.append({"ngay_dt":ngay_da_ghi, "ds":ds_duoi})
        # Sắp xếp lại theo thứ tự thời gian tăng dần để cắt đúng đủ 60 ngày gần nhất tính đến ngày vừa nhập
        LICH_SU_DU_LIEU.sort(key=lambda x:x["ngay_dt"])

        ngay_batdau = ngay_da_ghi - timedelta(days=59)
        ds_trong_60ngay = []
        # Chỉ lấy đúng những mục có ngày nằm trong khoảng từ bắt đầu đến ngày vừa nhập → mỗi ngày mới thay đổi tập hợp này
        for muc in LICH_SU_DU_LIEU:
            if muc["ngay_dt"] >= ngay_batdau and muc["ngay_dt"] <= ngay_da_ghi:
                ds_trong_60ngay.extend(muc["ds"])

        top3, top20 = tinh_diem_chuan(ds_trong_60ngay)
        bot.send_message(msg.chat.id,f"✅ **ĐÃ NHẬN ĐỦ DỮ LIỆU NGÀY: {ngay_da_ghi.strftime('%d/%m/%Y')}** ✅")
        bot.send_message(msg.chat.id,"⏳ Đã lọc chính xác đủ các ngày trong khoảng 60 ngày kết thúc đúng ngày này → phân tích theo tần suất & độ đều đặn...")
        nd = f"""🎯 KẾT QUẢ RIÊNG CHO GIAI ĐOẠN: {ngay_batdau.strftime('%d/%m/%Y')} ➡ {ngay_da_ghi.strftime('%d/%m/%Y')}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏆 TOP 3 ĐUÔI CÓ QUY LUẬT TỐT NHẤT:
1. 🥇 Đuôi {top3[0][0]} – xuất hiện {top3[0][1]} lần | cao nhất + chu kỳ đều ổn định nhất
2. 🥈 Đuôi {top3[1][0]} – xuất hiện {top3[1][1]} lần – tốt thứ hai
3. 🥉 Đuôi {top3[2][0]} – xuất hiện {top3[2][1]} lần – đáng tin cậy thứ ba

📋 DANH SÁCH MỞ RỘNG 20 ĐUÔI:
▫️ {'  ▫️ '.join(top20)}

⚠️ Chỉ tham khảo theo dữ liệu riêng giai đoạn này!
"""
        bot.send_message(msg.chat.id,nd)
        dang_cho[msg.chat.id] = False # Sẵn sàng nhận ngày sau hoàn toàn mới

    except Exception as e:
        bot.send_message(msg.chat.id,"⚠️ Gửi đúng danh sách đuôi cách dấu phẩy nhé!")

# === LỆNH NGAYMOC vẫn hoạt động chuẩn lưu riêng từng ngày không đè lên nhau ===
@bot.message_handler(func=lambda msg: msg.text.startswith("NGAYMOC|"))
def xu_ly_ngay_moc(msg):
    if msg.chat.id != CHAT_ID: return
    try:
        _, ngay_moc_str, danh_sach_duoi_str = msg.text.split("|",2)
        ngay_moc_str = ngay_moc_str.strip()
        ngay_moc = datetime.strptime(ngay_moc_str,"%d/%m/%Y")
        ds_ngay = [d.strip() for d in danh_sach_duoi_str.strip().split(",") if d.strip()]

        # 🟢 LUÔN THÊM MỚI KHÔNG VIẾT ĐÈ DỮ LIỆU CŨ → cửa sổ 60 ngày trượt theo đúng ngày được đưa vào
        LICH_SU_DU_LIEU.append({"ngay_dt":ngay_moc, "ds":ds_ngay})
        LICH_SU_DU_LIEU.sort(key=lambda x:x["ngay_dt"])

        ngay_batdau = ngay_moc - timedelta(days=59)
        ds_trong_60ngay = []
        for muc in LICH_SU_DU_LIEU:
            if muc["ngay_dt"] >= ngay_batdau and muc["ngay_dt"] <= ngay_moc:
                ds_trong_60ngay.extend(muc["ds"])

        top3, top20 = tinh_diem_chuan(ds_trong_60ngay)
        bot.send_message(msg.chat.id,f"✅ **ĐÃ LƯU & PHÂN TÍCH RIÊNG NGÀY: {ngay_moc_str}** ✅")
        nd = f"""🎯 KẾT QUẢ KHÁC BIỆT THEO ĐÚNG GIAI ĐOẠN: {ngay_batdau.strftime('%d/%m/%Y')} ➡ {ngay_moc_str}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏆 TOP 3 ĐUÔI ƯU TIÊN:
1. 🥇 Đuôi {top3[0][0]} – xuất hiện {top3[0][1]} lần
2. 🥈 Đuôi {top3[1][0]} – xuất hiện {top3[1][1]} lần
3. 🥉 Đuôi {top3[2][0]} – xuất hiện {top3[2][1]} lần

📋 DANH SÁCH MỞ RỘNG:
▫️ {'  ▫️ '.join(top20)}
"""
        bot.send_message(msg.chat.id,nd)
    except: bot.send_message(msg.chat.id,"⚠️ Dùng đúng mẫu: NGAYMOC|ngày/tháng/năm|đuôi1,đuôi2,...")

# === BÁO TRẠNG THÁI ===
def bao_dinh_ky():
    while True:
        gio_vn = datetime.utcnow() + timedelta(hours=7)
        bot.send_message(CHAT_ID,f"✅ BÁO HOẠT ĐỘNG: {gio_vn.strftime('%H:%M %d/%m/%Y')} | Đã sửa: mỗi ngày nhập dữ liệu riêng → kết quả riêng không trùng lặp nữa!")
        time.sleep(10800)
Thread(target=bao_dinh_ky, daemon=True).start()

@bot.message_handler(func=lambda msg: msg.text.strip() == "Trang thai")
def kiem_tra_nhanh(msg):
    if msg.chat.id != CHAT_ID: return
    bot.send_message(msg.chat.id,"✅ Đã khắc phục triệt để trùng kết quả:\n📌 Không còn viết cứng một bộ số duy nhất\n📌 Thêm dữ liệu mới giữ nguyên cũ, sắp xếp theo thời gian\n📌 Cắt chính xác đủ 60 ngày tính đến ngày bạn chọn → tập hợp số khác nhau → xếp hạng khác nhau rõ rệt\n📌 Vẫn giữ nguyên đúng công thức tính điểm đã thống nhất trước đó")

while True:
    try: bot.polling(none_stop=True, interval=5, timeout=60)
    except Exception as loi: print(f"Chờ kết nối lại: {loi}"); time.sleep(10)
