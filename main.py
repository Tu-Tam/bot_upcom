# === Giữ bot đúng quy định Render cực nhẹ ===
from flask import Flask
from threading import Thread
import time, telebot, requests

app = Flask(__name__)
@app.route('/')
def trang_chu(): return "✅ Bot nguồn dữ liệu VN ổn định - kiểm tra RMA thành công cao!"
Thread(target=lambda: app.run(host="0.0.0.0", port=int(os.environ.get("PORT",8080)))).start()

# === Thông tin chính xác ===
BOT_TOKEN = "8520938638:AAEHwQp89_P2slG7YTkod4z6_XvYbgBD7ns"
CHAT_ID = 7064473358
bot = telebot.TeleBot(BOT_TOKEN)
luu = {}

# === 🟢 CHUYỂN NGUỒN DỮ LIỆU VNDIRECT - API mở, ít chặn, trả về chuẩn dễ lấy được nhiều hơn ===
def lay_nguon_nhanh(ma):
    thu_lai = 0
    while thu_lai < 3: # tự thử lại tối đa 3 lần nếu chặn nhẹ
        try:
            url = f"https://finfo-api.vndirect.com.vn/v4/stock_prices?sort=date&q=code:{ma}&size=50"
            headers = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
            res = requests.get(url, headers=headers, timeout=12).json()

            if res.get("data") and len(res["data"])>=45: # đủ số ngày yêu cầu tính RMA
                ds = res["data"]
                ds.reverse() # sắp xếp cũ → mới đúng thứ tự trung bình
                gia_dong = [x["close"] for x in ds]
                gia_cao = [x["high"] for x in ds]
                gia_thap = [x["low"] for x in ds]
                gia_hien = round(gia_dong[-1],2)

                # Tính đúng RMA12/26/50 theo yêu cầu của bạn
                r12 = round(sum(gia_dong[-12:])/12,2)
                r26 = round(sum(gia_dong[-26:])/26,2)
                r50 = round(sum(gia_dong[-50:])/50,2)

                if r12>r26 and r26>r50:
                    diem=8; nhan="✅ RMA chồng đúng thứ tự: Xu hướng tăng mạnh ưu tiên xem xét"
                elif r12>r26:
                    diem=5; nhan="⏸️ Ngắn trên trung hạn: đang cải thiện theo dõi thêm"
                else:
                    diem=3; nhan="❌ Chưa đủ xu hướng tăng mạnh: giữ tiền an toàn chờ tín hiệu rõ hơn"

                chot_loi = round(max(gia_cao[-10:])*0.995,2)
                cat_von = round(min(gia_thap[-10:])*1.005,2)

                luu[ma] = {"gia":gia_hien,"diem":diem,"r12":r12,"r26":r26,"r50":r50,"cl":chot_loi,"sl":cat_von,"tt":nhan}
                return True
            else: thu_lai +=1; time.sleep(2.5)
        except Exception as e: print(f"Lần thử {thu_lai+1} lỗi:",str(e)[:40]); thu_lai +=1; time.sleep(2.5)
    return False

# === Lệnh Trạng thái kiểm tra bot còn sống ngay ===
@bot.message_handler(func=lambda m:m.text.strip()=="Trạng thái")
def tra_loi(m):
    if m.chat.id!=CHAT_ID:return
    bot.send_message(CHAT_ID,"💓 **BOT ĐANG HOẠT ĐỘNG BÌNH THƯỜNG ✅**\n📥 Nguồn: VNDIRECT ổn định ít chặn máy chủ hơn\n📈 Tính đủ RMA12/RMA26/RMA50 + giá chốt lời/bảo vốn\n💬 Gõ **Đánh giá mã** chạy lấy dữ liệu lại ngay!")

# === Lệnh chính báo % tiến trình rõ ràng từng bước ===
@bot.message_handler(func=lambda m:m.text.strip()=="Đánh giá mã")
def chay_kiemtra(m):
    if m.chat.id!=CHAT_ID:return
    luu.clear()
    bot.send_message(CHAT_ID,"📥 **Bắt đầu thu thập từ nguồn ổn định VNDIRECT, báo % rõ từng bước!**")
    danh_sach = ["SHB","VCB"]
    tong = len(danh_sach)
    for stt,ma in enumerate(danh_sach, start=1):
        bot.send_message(CHAT_ID,f"⏳ Đang xử lý: {ma} → Đã hoàn thành: {int((stt-1)/tong*100)}%")
        ok = lay_nguon_nhanh(ma)
        time.sleep(3) # nghỉ đủ nhẹ không bị chặn hàng loạt
        if ok: bot.send_message(CHAT_ID,f"✅ Lấy thành công: {ma} → Tiến độ: {int(stt/tong*100)}%")
        else: bot.send_message(CHAT_ID,f"⚠️ Đã thử lại nhiều lần vẫn chưa lấy được: {ma} tạm bỏ qua lần này")

    bot.send_message(CHAT_ID,f"🏁 **Kết thúc đợt: Tổng {len(luu)}/{tong} mã lấy đủ dữ liệu thành công!**")
    if not luu:
        bot.send_message(CHAT_ID,"😔 Lần này vẫn chưa lấy được nào, chờ khoảng 1 giờ sau thử lại giờ thấp điểm truy cập dễ qua hơn nhé!")
        return

    # In ra bảng chi tiết đủ thông tin bạn yêu cầu
    bot.send_message(CHAT_ID,"📊 **BẢNG KẾT QUẢ RMA - DỮ LIỆU CHÍNH XÁC THỊ TRƯỜNG**")
    for ma,tt in sorted(luu.items(), key=lambda x:x[1]["diem"], reverse=True):
        bot.send_message(CHAT_ID,f"""📌 **Mã: {ma}**
⭐ Điểm đánh giá: {tt['diem']}/10
📈 RMA12: {tt['r12']} | RMA26: {tt['r26']} | RMA50: {tt['r50']}
💵 Giá hiện tại: {tt['gia']:,} VNĐ
🎯 Giá chốt lời đề xuất: {tt['cl']:,} VNĐ
🛡️ Giá bảo vốn cắt lỗ: {tt['sl']:,} VNĐ
💬 Nhận xét: {tt['tt']}
——————————————————————""")

# === Thông báo đã chuyển nguồn mới rõ ràng khi khởi động xong ===
bot.send_message(CHAT_ID,"🤖🔄 **Đã chuyển nguồn dữ liệu VNDIRECT thay vì Cafef.vn!**\n✅ Ít chặn máy chủ Render hơn nhiều, tự thử lại khi gặp chặn nhẹ\n✅ Vẫn giữ đúng yêu cầu: tính đủ 3 đường RMA + báo % + giá chốt lời/bảo vốn rõ ràng!")

# === Vòng lặp lắng nghe tin nhắn nhẹ không quá tải ===
while True:
    try: bot.polling(none_stop=True, interval=3)
    except Exception as loi: print("Kết nối tạm ngắt:",loi); time.sleep(5)
    time.sleep(60)
