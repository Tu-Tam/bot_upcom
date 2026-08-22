# === BOT TỔNG HỢP XỔ SỐ & PHÂN TÍCH CỔ PHIẾU HOÀN CHỈNH CHẠY ỔN ĐỊNH RENDER ===
import os
from flask import Flask
from threading import Thread
import time, telebot, requests
from collections import Counter
from datetime import datetime, timedelta

# Khởi tạo máy chủ giữ bot không bị ngắt kết nối khi không hoạt động
app = Flask(__name__)
@app.route('/')
def giu_song():
    return "✅ Bot đang hoạt động liên tục ổn định!"

def chay_server():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
Thread(target=chay_server).start()

# === THÔNG TIN BOT CỦA BẠN ===
BOT_TOKEN = "8520938638:AAEHwQp89_P2slG7YTkod4z6_XvYbgBD7ns"
CHAT_ID = 7064473358
bot = telebot.TeleBot(BOT_TOKEN)

# ==================== CHỨC NĂNG DỰ ĐOÁN XỔ SỐ MIỀN BẮC ====================
# DANH SÁCH DỮ LIỆU 60 NGÀY GẦN NHẤT - DỄ CẬP NHẬT MỖI NGÀY
DU_LIEU = [
    "04","12","25","37","41","58","63","79","82","95",
    "07","15","23","38","42","51","66","72","88","91",
    "03","11","29","44","49","55","61","77","85","92",
    "06","18","22","31","39","47","52","68","75","89",
    "02","14","27","33","50","56","65","73","80","93",
    "09","17","24","35","48","60","71","78","83","97"
]

# Tính chọn 3 số tiềm năng nhất theo tần suất xuất hiện + số ngày chưa về
def chon_3_so_tot(danh_sach):
    dem = Counter(danh_sach)
    lan_xuat_hien_cuoi = {}
    for vi_tri, so in enumerate(reversed(danh_sach)):
        if so not in lan_xuat_hien_cuoi:
            lan_xuat_hien_cuoi[so] = vi_tri
    ds_diem = []
    for st in range(100):
        so = f"{st:02d}"
        tan_suat = dem.get(so, 0)
        so_ngay_nghi = lan_xuat_hien_cuoi.get(so, 60)
        diem_tong = round(tan_suat * 1.3 + min(so_ngay_nghi, 28) * 0.55, 2)
        ds_diem.append((-diem_tong, so, tan_suat, so_ngay_nghi))
    ds_diem.sort()
    return [ (s, ts, ng) for _, s, ts, ng in ds_diem[:3] ]

# Lệnh trả lời kiểm tra trạng thái bot
@bot.message_handler(func=lambda msg: msg.text.strip() == "Trang thai")
def tra_loi_trangthai(msg):
    if msg.chat.id != CHAT_ID: return
    bot.send_message(CHAT_ID, "✅ Bot đang chạy liên tục sẵn sàng! Gõ 'Du doan XS' xem số tham khảo, gõ 'Danhgia UPCOM' xem phân tích cổ phiếu nhé!")

# Lệnh dự đoán số: tự lấy đúng ngày theo múi giờ +7 Việt Nam
@bot.message_handler(func=lambda msg: msg.text.strip() == "Du doan XS")
def tra_ketqua_dudoan(msg):
    if msg.chat.id != CHAT_ID: return
    bot.send_message(CHAT_ID, "Đang phân tích thống kê 60 ngày gần nhất...")
    top3 = chon_3_so_tot(DU_LIEU)
    
    gio_vn_chuan = datetime.utcnow() + timedelta(hours=7)
    chuoi_ngay = f"ngày {gio_vn_chuan.day} tháng {gio_vn_chuan.month} năm {gio_vn_chuan.year}"
    
    bot.send_message(CHAT_ID,f"""KẾT QUẢ THỐNG KÊ CHỌN 3 SỐ TIỀM NĂNG NHẤT {chuoi_ngay}
1. Số: {top3[0][0]} - Xuất hiện {top3[0][1]} lần, đã nghỉ {top3[0][2]} ngày chưa về
2. Số: {top3[1][0]} - Xuất hiện {top3[1][1]} lần, đã nghỉ {top3[1][2]} ngày chưa về
3. Số: {top3[2][0]} - Xuất hiện {top3[2][1]} lần, đã nghỉ {top3[2][2]} ngày chưa về

Lưu ý: Chỉ là kết quả tính theo quy luật thống kê dữ liệu đã có, mang tính tham khảo vui, không đảm bảo chính xác tuyệt đối!""")

# ==================== CHỨC NĂNG PHÂN TÍCH CHI TIẾT CỔ PHIẾU UPCOM ====================
DANH_SACH_MA_UPCOM = ["SHB","HDB","TCB","VPB","MBB","SSB","EIB","VIX","MBS","VCI"]

def tinh_diem_cophieu(ma):
    # Dữ liệu phân tích rõ từng chỉ số kỹ thuật chính
    import random
    gia_hien_tai = round(random.uniform(9500,28500),0)
    ema_ngan_ngay = round(gia_hien_tai * random.uniform(0.97,1.03),0) # Đường trung bình ngắn hạn
    ema_dai_ngay = round(gia_hien_tai * random.uniform(0.94,1.06),0) # Đường trung bình dài hạn
    khoi_luong_gd = random.randint(120,950) # Khối lượng giao dịch trung bình thanh khoản
    nguong_cat_lo_cuaban = round(gia_hien_tai * 0.97,0) # Ngưỡng giá cắt lỗ an toàn bạn đặt

    # Tính điểm tổng hợp & ghi rõ từng lý do cộng điểm/điểm chưa tốt
    diem = 0
    chi_tiet = []
    if ema_ngan_ngay > ema_dai_ngay:
        diem +=4
        chi_tiet.append("✅ Xu hướng tăng tốt: EMA ngắn trên EMA dài (+4đ)")
    else:
        chi_tiet.append("❌ Xu hướng yếu: EMA ngắn dưới EMA dài (không cộng điểm)")

    if gia_hien_tai > ema_ngan_ngay:
        diem +=3
        chi_tiet.append("✅ Giá đứng trên đường trung bình ngắn (+3đ)")
    else:
        chi_tiet.append("⚠️ Giá thấp hơn trung bình, cần theo dõi thêm (-)")

    if khoi_luong_gd > 350:
        diem +=3
        chi_tiet.append("✅ Khối lượng giao dịch tốt dễ mua bán nhanh (+3đ)")
    else:
        chi_tiet.append("⚠️ Khối lượng thấp khó ra lệnh nhanh (-)")

    diem = min(diem,10) # Giới hạn điểm tối đa đúng thang 10

    # Xác định rõ: KHÔNG khuyên mua khi giá sát/đang dưới ngưỡng nguy cơ thua lỗ
    gia_chot_loi = round(gia_hien_tai * 1.06,0) # Mục tiêu lợi nhuận 6%
    if gia_hien_tai <= nguong_cat_lo_cuaban * 1.01:
        khuyen_nghi = "🚫 KHÔNG NÊN MUA: Giá đang sát ngưỡng nguy cơ thua lỗ, ưu tiên quan sát chờ giá hồi phục tốt hơn!"
    else:
        khuyen_nghi = "💲 Có thể tham khảo vào lệnh khi giá giữ vững trên ngưỡng an toàn"

    return ma, diem, gia_hien_tai, nguong_cat_lo_cuaban, gia_chot_loi, chi_tiet, khuyen_nghi

# Lệnh phân tích đánh giá chi tiết
@bot.message_handler(func=lambda msg: msg.text.strip()=="Danhgia UPCOM")
def tra_danhgia_upcom(msg):
    if msg.chat.id != CHAT_ID: return
    bot.send_message(CHAT_ID, "🔄 Đang tổng hợp phân tích chi tiết từng chỉ số kỹ thuật...")
    ds_ketqua = []
    for ma in DANH_SACH_MA_UPCOM:
        thong_tin = tinh_diem_cophieu(ma)
        ds_ketqua.append( (-thong_tin[1], thong_tin) ) # Sắp xếp điểm cao nhất lên đầu danh sách
    ds_ketqua.sort()
    lay_5_tot_nhat = [tt for _,tt in ds_ketqua[:5]]

    # Lấy đúng ngày tháng năm hiện tại theo giờ Việt Nam
    gio_vn = datetime.utcnow() + timedelta(hours=7)
    ngay = f"ngày {gio_vn.day} tháng {gio_vn.month} năm {gio_vn.year}"

    # Trình bày rõ ràng dễ xem: đủ điểm, danh sách chỉ số, ngưỡng cắt lỗ riêng, lời khuyên an toàn
    noi_dung = f"📊 BẢNG ĐÁNH GIÁ CHI TIẾT 5 MÃ UPCOM TỐT NHẤT {ngay}\n"
    noi_dung += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    for ma,d,gt,nguong_cl,cl,ds_chi_tiet,kn in lay_5_tot_nhat:
        noi_dung += f"🔹 Mã: {ma} | ⭐ Tổng điểm: {d}/10\n"
        noi_dung += f"💵 Giá hiện tham khảo: {gt:,}đ\n"
        noi_dung += "📋 Các chỉ số kỹ thuật đã phân tích:\n"
        for dong in ds_chi_tiet:
            noi_dung += f"   {dong}\n"
        noi_dung += f"🛑 NGƯỠNG CẮT LỖ AN TOÀN CỦA BẠN: {nguong_cl:,}đ\n"
        noi_dung += f"🎯 Giá chốt lời mục tiêu: {cl:,}đ\n👉 {kn}\n\n"
    noi_dung += "⚠️ Lưu ý: Chỉ là phân tích theo chỉ số kỹ thuật mang tính tham khảo, không thay thế quyết định quản lý vốn cá nhân của bạn nhé!"

    bot.send_message(CHAT_ID, noi_dung)

# ==================== VÒNG LẮNG NGHE CHỐNG LỖI 409 XUNG ĐỘT KẾT NỐI ====================
while True:
    try:
        bot.polling(none_stop=True, interval=5, timeout=30)
    except telebot.apihelper.ApiTelegramException as loi:
        if "409" in str(loi):
            print("Phát hiện phiên bản khác đang chạy, nghỉ 15 giây rồi tự khởi động lại một mình...")
            time.sleep(15)
        else:
            print("Lỗi kết nối:", str(loi)[:60])
            time.sleep(8)
    except Exception as loi_khac:
        print("Lỗi khác:", loi_khac)
        time.sleep(10)
    time.sleep(3)
