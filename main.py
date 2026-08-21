# === Giữ bot luôn hoạt động đúng quy định Render ===
from flask import Flask
from threading import Thread
import time, telebot, requests

app = Flask(__name__)
@app.route('/')
def trang_chu():
    return "✅ Bot lấy CAFEF.VN | Kiểm tra RMA12/26/50 đang chạy ổn định!"

def chay_server():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
Thread(target=chay_server).start()

# === Thông tin kết nối chính xác ===
BOT_TOKEN = "8520938638:AAEHwQp89_P2slG7YTkod4z6_XvYbgBD7ns"
CHAT_ID = 7064473358
bot = telebot.TeleBot(BOT_TOKEN)
luu = {}

# === Lấy dữ liệu đúng nguồn Cafef.vn đơn giản nhất ===
def lay_cafef(ma):
    try:
        url = f"https://s.cafef.vn/Ajax/PageNew/DataHistory/PriceHistory.ashx?Symbol={ma}&StartDate=&EndDate=&GetAll=true"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": f"https://s.cafef.vn/lich-su-gia-{ma}.chn"
        }
        res = requests.get(url, headers=headers, timeout=10).json()
        if "Data" in res and "Data" in res["Data"]:
            ds = res["Data"]["Data"][:50]
            ds.reverse()
            g_d = [float(x["ClosePrice"]) for x in ds]
            g_c = [float(x["HighestPrice"]) for x in ds]
            g_t = [float(x["LowestPrice"]) for x in ds]
            g_h = round(g_d[-1],2)

            # Tính đúng RMA yêu cầu
            r12 = round(sum(g_d[-12:])/12,2)
            r26 = round(sum(g_d[-26:])/26,2)
            r50 = round(sum(g_d[-50:])/50,2)

            if r12>r26 and r26>r50:
                diem=8; tb="✅ TỐT: RMA tăng đúng thứ tự ưu tiên xem xét"
            elif r12>r26:
                diem=5; tb="⏸️ TRUNG BÌNH: ngắn trên trung hạn theo dõi thêm"
            else:
                diem=3; tb="❌ YẾU: chưa đủ xu hướng mạnh chưa vào lệnh"

            cl=round(max(g_c[-8:])*0.995,2)
            sl=round(min(g_t[-8:])*1.005,2)
            luu[ma]={"gia":g_h,"diem":diem,"r12":r12,"r26":r26,"r50":r50,"cl":cl,"sl":sl,"tb":tb}
            return True
    except Exception as e:
        print("Lỗi:",e)
    return False

# === Lệnh đơn giản dễ nhận biết phản hồi ===
@bot.message_handler(func=lambda m:m.text.strip()=="Trạng thái")
def tra(m):
    if m.chat.id!=CHAT_ID:return
    bot.send_message(CHAT_ID,"💓 Đang hoạt động ✅\n📥 Nguồn: CAFEF.VN\n📈 RMA12/RMA26/RMA50\n💬 Gõ: Đánh giá mã xem kết quả SHB,VCB")

@bot.message_handler(func=lambda m:m.text.strip()=="Đánh giá mã")
def xem(m):
    if m.chat.id!=CHAT_ID:return
    bot.send_message(CHAT_ID,"🔄 Đang lấy số liệu mới nhất từ CAFEF.VN... chờ lát nhé!")
    luu.clear()
    for ma in ["SHB","VCB"]:
        lay_cafef(ma); time.sleep(2.5)
    if not luu:
        bot.send_message(CHAT_ID,"⚠️ Lần này chưa lấy được, thử lại sau chốc nữa nhé!")
        return
    bot.send_message(CHAT_ID,"📊 **KẾT QUẢ KIỂM TRA RMA - CAFEF.VN**")
    for ma,tt in sorted(luu.items(), key=lambda x:x[1]["diem"], reverse=True):
        bot.send_message(CHAT_ID,f"""📌 {ma} | Điểm: {tt['diem']}/10
📈 RMA12:{tt['r12']} RMA26:{tt['r26']} RMA50:{tt['r50']}
💵 Giá: {tt['gia']:,}đ
🎯 Chốt lời: {tt['cl']:,}đ
🛡️ Bảo vốn: {tt['sl']:,}đ
💬 {tt['tb']}""")

# === Thông báo khởi động thành công rõ ràng ===
bot.send_message(CHAT_ID,"🤖✅ Đã cập nhật bản gọn sửa lỗi triển khai!\n📥 Nguồn đúng CAFEF.VN\n💬 Gõ Trạng thái xem phản hồi nhanh nhé!")

# === Vòng lặp đơn giản ổn định không gây quá tải ===
while True:
    try: bot.polling(none_stop=True, interval=3)
    except Exception as e: print("Kết nối:",e); time.sleep(5)
    time.sleep(60)
