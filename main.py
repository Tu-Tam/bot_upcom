# === GIỮ BOT LUÔN HOẠT ĐỘNG ===
from flask import Flask
from threading import Thread
import time, telebot, requests, json

app = Flask('')
@app.route('/')
def trang_chu(): return "✅ Bot lấy dữ liệu CAFEF.VN - kiểm tra RMA nhanh"
Thread(target=lambda: app.run(host="0.0.0.0", port=int(os.environ.get("PORT",8080)))).start()

# === THÔNG TIN KẾT NỐI ===
BOT_TOKEN = "8520938638:AAEHwQp89_P2slG7YTkod4z6_XvYbgBD7ns"
CHAT_ID = 7064473358
bot = telebot.TeleBot(BOT_TOKEN)
luu_ketqua = {}

# === 🟢 LẤY DỮ LIỆU CHÍNH TỪ CAFEF.VN ===
def lay_gia_tu_cafef(ma):
    try:
        # Gọi đúng đường dẫn cung cấp dữ liệu lịch sử giá của Cafef.vn
        url = f"https://s.cafef.vn/Ajax/PageNew/DataHistory/PriceHistory.ashx?Symbol={ma}&StartDate=&EndDate=&GetAll=true"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": f"https://s.cafef.vn/lich-su-gia-{ma}.chn"
        }
        res = requests.get(url, headers=headers, timeout=12).json()

        if res.get("Data") and res["Data"].get("Data"):
            danh_sach = res["Data"]["Data"][:50] # lấy 50 phiên gần nhất đủ tính RMA
            danh_sach.reverse() # sắp xếp từ cũ đến mới đúng thứ tự tính trung bình
            gia_dong = []
            gia_cao = []
            gia_thap = []
            for item in danh_sach:
                gia_dong.append(float(item["ClosePrice"]))
                gia_cao.append(float(item["HighestPrice"]))
                gia_thap.append(float(item["LowestPrice"]))

            # === TÍNH CHÍNH XÁC RMA 12/26/50 NHƯ YÊU CẦU ===
            rma12 = round(sum(gia_dong[-12:])/12,2)
            rma26 = round(sum(gia_dong[-26:])/26,2)
            rma50 = round(sum(gia_dong[-50:])/50,2)
            gia_hien = round(gia_dong[-1],2)

            # Đánh giá xu hướng theo vị trí các đường RMA
            if rma12>rma26 and rma26>rma50:
                diem=8; tin="✅ RMA chồng lên đúng thứ tự - Xu hướng tăng mạnh ưu tiên xem xét"
            elif rma12>rma26:
                diem=5; tin="⏸️ RMA ngắn trên trung hạn - đang cải thiện theo dõi thêm"
            else:
                diem=3; tin="❌ RMA chưa tăng đúng thứ tự - còn yếu chưa vào lệnh"

            # Tính giá chốt lời & bảo vốn rõ ràng
            chot_loi = round(max(gia_cao[-10:])*0.995,2)
            cat_lo = round(min(gia_thap[-10:])*1.005,2)

            luu_ketqua[ma] = {
                "gia":gia_hien, "diem":diem,
                "r12":rma12, "r26":rma26, "r50":rma50,
                "cl":chot_loi, "sl":cat_lo, "tt":tin
            }
            return True
    except Exception as e: print("Lỗi lấy Cafef.vn:",e)
    return False

# === LỆNH TRẠNG THÁI KIỂM TRA BOT CÒN CHẠY ===
@bot.message_handler(func=lambda m:m.text.strip()=="Trạng thái")
def tra_loi(m):
    if m.chat.id!=CHAT_ID:return
    bot.send_message(CHAT_ID,"💓 **ĐANG HOẠT ĐỘNG** ✅\n📥 Nguồn số liệu: CAFEF.VN\n📈 Chỉ kiểm tra RMA12/RMA26/RMA50\n💬 Gõ **Đánh giá mã**: SHB, VCB xem ngay kết quả!")

# === LỆNH ĐÁNH GIÁ LẤY & HIỂN THỊ ĐỦ THÔNG TIN ===
@bot.message_handler(func=lambda m:m.text.strip()=="Đánh giá mã")
def hien_bao_cao(m):
    if m.chat.id!=CHAT_ID:return
    bot.send_message(CHAT_ID,"📥 Đang lấy dữ liệu mới nhất từ CAFEF.VN... chờ lát nhé!")
    luu_ketqua.clear()
    for ma in ["SHB","VCB"]:
        lay_gia_tu_cafef(ma)
        time.sleep(3) # nghỉ nhẹ truy cập ổn định không bị chặn

    if not luu_ketqua:
        bot.send_message(CHAT_ID,"⚠️ Tạm thời chưa lấy được, thử lại sau vài phút nhé!")
        return
    # Sắp xếp điểm cao hiển thị trước dễ chọn
    bot.send_message(CHAT_ID,"📊 **BẢNG KẾT QUẢ KIỂM TRA RMA - NGUỒN CAFEF.VN**")
    for ma,tt in sorted(luu_ketqua.items(), key=lambda x:x[1]["diem"], reverse=True):
        bot.send_message(CHAT_ID,f"""📌 **Mã: {ma}**
⭐ Điểm đánh giá: {tt['diem']}/10
📈 RMA12: {tt['r12']} | RMA26: {tt['r26']} | RMA50: {tt['r50']}
💵 Giá hiện tại: {tt['gia']:,} VNĐ
🎯 Giá chốt lời đề xuất: {tt['cl']:,} VNĐ
🛡️ Giá bảo vốn cắt lỗ: {tt['sl']:,} VNĐ
💬 Nhận xét: {tt['tt']}
——————————————————————""")

# === THÔNG BÁO KHỞI ĐỘNG THÀNH CÔNG ===
bot.send_message(CHAT_ID,"🤖✅ **Đã chuyển đúng lấy dữ liệu từ CAFEF.VN theo yêu cầu!**\n⚙️ Tính RMA chính xác từ giá đóng cửa từng ngày\n💬 Gõ Trạng thái / Đánh giá mã kiểm tra hoạt động nhé!")

# === VÒNG LẮNG NGHE LỆNH ỔN ĐỊNH ===
while True:
    try: bot.polling(none_stop=True, interval=3)
    except Exception as loi: print("Kết nối:",loi); time.sleep(5)
    time.sleep(60)
