# === BOT HOÀN CHỈNH: LOGIC THỐNG KÊ CHUẨN ĐUÔI GIẢI ĐẶC BIỆT ===
import os
from flask import Flask
from threading import Thread
import time, telebot
from collections import Counter
from datetime import datetime, timedelta

# === Giữ bot chạy liên tục trên Render ===
app = Flask(__name__)
@app.route('/')
def giu_song():
    return "✅ Bot đang hoạt động ổn định!"
def chay_server():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
Thread(target=chay_server).start()

# === THÔNG TIN BOT ===
BOT_TOKEN = "8520938638:AAEHwQp89_P2slG7YTkod4z6_XvYbgBD7ns"
CHAT_ID = 7064473358
bot = telebot.TeleBot(BOT_TOKEN)

# === DỮ LIỆU LỊCH SỬ: CHỈ LẤY NHỮNG NGÀY TRƯỚC, KHÔNG CHỨA KẾT QUẢ HÔM NAY ===
DU_LIEU_LICH_SU = [
    "04","12","25","37","41","58","63","79","82","95",
    "07","15","23","38","42","51","66","72","88","91",
    "03","11","29","44","49","55","61","77","85","92",
    "06","18","22","31","39","47","52","68","75","89",
    "02","14","27","33","50","56","65","73","80","93",
    "09","17","24","35","48","60","71","78","83","97"
]
# Kết quả hôm nay chỉ ghi riêng để đối chiếu sau, tuyệt đối không trộn vào tính toán làm lệch chu kỳ gốc
DUOI_THUC_TE_HOMNAY = "00"

# === HÀM TÍNH TOÁN LOGIC CHUẨN: CÂN BẰNG TẦN SUẤT XUẤT HIỆN + SỐ NGÀY ĐÃ NGHỈ CHƯA QUAY LẠI ===
def phan_tich_logich_chuan(danh_sach_lich_su):
    dem_so_lan = Counter(danh_sach_lich_su)
    ngay_nghi_chua_ve = {}
    # Đếm chính xác số ngày nghỉ kể từ lần xuất hiện cuối cùng
    for vi_tri, ma_duoi in enumerate(reversed(danh_sach_lich_su)):
        if ma_duoi not in ngay_nghi_chua_ve:
            ngay_nghi_chua_ve[ma_duoi] = vi_tri

    ds_diem = []
    for st in range(100):
        ma_duoi = f"{st:02d}"
        tan_suat = dem_so_lan.get(ma_duoi, 0)
        thoi_gian_nghi = ngay_nghi_chua_ve.get(ma_duoi, 60) # chưa từng ra tính nghỉ đủ 60 ngày tích lũy cao
        # TRỌNG SỐ BẰNG NHAU = CÂN BẰNG CHUẨN: vừa đều đặn vừa nghỉ đủ lâu
        diem_tong = round(tan_suat * 1.0 + min(thoi_gian_nghi, 30) * 1.0, 2)
        ds_diem.append( (-diem_tong, ma_duoi, tan_suat, thoi_gian_nghi) )

    ds_diem.sort() # điểm cao nhất lên đầu ưu tiên nhất
    top3 = [ (s,ts,ng) for _,s,ts,ng in ds_diem[:3] ]
    top20 = [ s for _,s,_,_ in ds_diem[:20] ]
    return top3, top20

# === LỆNH NHẬN YÊU CẦU TRẢ KẾT QUẢ ===
@bot.message_handler(func=lambda msg: msg.text.strip() == "Du doan XS")
def tra_ketqua(msg):
    if msg.chat.id != CHAT_ID: return
    bot.send_message(CHAT_ID,"🔄 Đang phân tích theo logic chuẩn: tách dữ liệu trước ngày, cân bằng đều đặn + nghỉ lâu chưa về...")
    top3, top20 = phan_tich_logich_chuan(DU_LIEU_LICH_SU)
    gio_vn = datetime.utcnow() + timedelta(hours=7)
    ngay = f"ngày {gio_vn.day} tháng {gio_vn.month} năm {gio_vn.year}"

    noi_dung = f"""🎯 KẾT QUẢ CHỌN LỌC ĐUÔI GIẢI ĐẶC BIỆT {ngay}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏆 3 ĐUÔI CÓ TỔNG ĐIỂM CAO NHẤT:
1. Đuôi {top3[0][0]} | Xuất hiện {top3[0][1]} lần, đã nghỉ {top3[0][2]} ngày chưa quay lại
2. Đuôi {top3[1][0]} | Xuất hiện {top3[1][1]} lần, đã nghỉ {top3[1][2]} ngày chưa quay lại
3. Đuôi {top3[2][0]} | Xuất hiện {top3[2][1]} lần, đã nghỉ {top3[2][2]} ngày chưa quay lại

📋 DANH SÁCH ĐỦ 20 ĐUÔI ƯU TIÊN THEO DÕI GIẢI ĐẶC BIỆT:
▫️ {'  ▫️ '.join(top20)}

✅ Đã tính hoàn toàn tách riêng dữ liệu lịch sử trước ngày, không dùng kết quả thực tế '{DUOI_THUC_TE_HOMNAY}' vào làm thay đổi chu kỳ gốc!
📌 Tiêu chí: Ưu tiên đuôi vừa xuất hiện đều đặn trong quá khứ, vừa đã qua nhiều ngày chưa quay lại theo đúng quy luật luân phiên thống kê!
⚠️ Chỉ phân tích theo quy luật dữ liệu đã có, mang tính tham khảo vui, chơi có trách nhiệm, không đảm bảo trúng chắc chắn tuyệt đối!
"""
    bot.send_message(CHAT_ID, noi_dung)

# === Lệnh kiểm tra trạng thái bot ===
@bot.message_handler(func=lambda msg: msg.text.strip() == "Trang thai")
def kiem_tra_tt(msg):
    if msg.chat.id != CHAT_ID: return
    bot.send_message(CHAT_ID,"✅ Bot đang chạy ổn định!\n📌 Lệnh dùng: Trang thai | Du doan XS")

# === Vòng chạy bền, tự khởi động lại khi mất kết nối ===
while True:
    try:
        bot.polling(none_stop=True, interval=5, timeout=30)
    except telebot.apihelper.ApiTelegramException as loi:
        if "409" in str(loi):
            print("Đã có phiên chạy khác, nghỉ ngắn rồi khởi động lại...")
            time.sleep(15)
        else:
            print(f"Lỗi kết nối: {loi}")
            time.sleep(8)
    except Exception as e:
        print(f"Lỗi khác: {e}")
        time.sleep(10)
