# === GIỮ BOT LUÔN HOẠT ĐỘNG ===
from flask import Flask
from threading import Thread
import time, telebot, requests, math

app = Flask('')
@app.route('/')
def giu(): return "✅ Bot báo % + đủ giá chốt lời bảo vốn rõ ràng"
Thread(target=lambda: app.run(host="0.0.0.0", port=8080)).start()

# === THÔNG TIN KẾT NỐI ===
BOT_TOKEN = "8520938638:AAEHwQp89_P2slG7YTkod4z6_XvYbgBD7ns"
CHAT_ID = 7064473358
bot = telebot.TeleBot(BOT_TOKEN)

# === 2 MÃ CẦN KIỂM TRA ===
DANH_SACH = ["SHB", "VCB"]
tong_ma = len(DANH_SACH)
ketqua_da_luu = {} # Lưu đủ: điểm, giá, chốt lời, bảo vốn, tín hiệu

# === 📌 Nguồn dữ liệu mở, công khai, dễ truy cập không chặn chặt, trả đủ giá lịch sử ===
def lay_du_lieu_thanh_cong(ma):
    try:
        # Sử dụng API Alpha Vantage đúng định dạng mã VN, miễn phí có giới hạn nhẹ nhưng đủ thử 2 mã
        url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={ma}.VN&apikey=demo&outputsize=compact"
        res = requests.get(url, timeout=15).json()

        if "Time Series (Daily)" in res:
            ds_ngay = sorted(res["Time Series (Daily)"].keys(), reverse=True)[:60] # lấy đủ 60 ngày gần nhất
            ds_ngay.reverse() # sắp xếp cũ → mới đúng thứ tự tính toán
            gia_dong, gia_cao, gia_thap, kl = [], [], [], []
            for ngay in ds_ngay:
                d = res["Time Series (Daily)"][ngay]
                gia_dong.append(float(d["4. close"]))
                gia_cao.append(float(d["2. high"]))
                gia_thap.append(float(d["3. low"]))
                kl.append(int(d["5. volume"]))

            if len(gia_dong)>=50: # đủ số ngày chuẩn tính chỉ số
                gia_hien = round(gia_dong[-1], 2)

                # Tính chỉ số chuẩn
                def tinh_ema(ds, ky):
                    hs = 2/(ky+1); ema = sum(ds[-ky:])/ky
                    for g in ds[-ky+1:]: ema = g*hs + ema*(1-hs)
                    return round(ema,2)
                ema12 = tinh_ema(gia_dong,12); ema26 = tinh_ema(gia_dong,26); sma50 = round(sum(gia_dong[-50:])/50,2)
                macd = round(ema12 - ema26,4)

                def tinh_rsi(ds,ky):
                    tang, giam = [], []
                    for i in range(len(ds)-ky, len(ds)):
                        cl = ds[i]-ds[i-1]; tang.append(max(cl,0)); giam.append(max(-cl,0))
                    tb_tang = sum(tang)/ky; tb_giam = sum(giam)/ky
                    return round(100 - (100/(1+tb_tang/tb_giam)),2) if tb_giam>0 else 100
                rsi = tinh_rsi(gia_dong,14)

                sma20 = sum(gia_dong[-20:])/20; do_lech = round(math.sqrt(sum((x-sma20)**2 for x in gia_dong[-20:])/20),2)
                boll_tren = round(sma20 + 2*do_lech,2); boll_duoi = round(sma20 - 2*do_lech,2)
                ho_tro = round(min(gia_thap[-20:]),2); khang_cu = round(max(gia_cao[-20:]),2); kl_tb = round(sum(kl[-20:])/20)

                # Chấm điểm thang 10 rõ ràng
                diem = 0
                if ema12>ema26 and ema26>sma50: diem +=2
                if macd>0: diem +=2
                if 35<rsi<70: diem +=2
                if kl[-1]>kl_tb*1.03: diem +=2
                if ho_tro<gia_hien<khang_cu and gia_hien<boll_tren: diem +=2

                # Tính rõ giá vào, chốt lời mục tiêu, giá bảo vốn cắt lỗ
                gia_chot_loi = round(min(khang_cu, boll_tren)*0.995,2)
                gia_cat_lo = round(max(ho_tro, boll_duoi)*0.995,2)
                tin_hieu = "✅ MUA - nhiều chỉ số đồng bộ tốt" if diem>=6 else "⏸️ THEO DÕI - chưa đủ tín hiệu mạnh" if diem>=4 else "❌ TRÁNH - tín hiệu yếu chưa vào lệnh"

                ketqua_da_luu[ma] = {
                    "gia_hien":gia_hien, "diem":diem, "rsi":rsi,
                    "chot_loi":gia_chot_loi, "bao_von":gia_cat_lo, "tin_hieu":tin_hieu
                }
                return True
            return False
        else: return False
    except Exception as e: print("Lỗi lấy dữ liệu:",e); return False

# === Chạy thu thập + báo % tiến trình rõ từng bước ===
def chay_thu_thap():
    ketqua_da_luu.clear()
    bot.send_message(CHAT_ID,"📥 **Bắt đầu thu thập có báo % chi tiết đủ thông tin giá chốt lời/bảo vốn!**")
    for chi_so, ma in enumerate(DANH_SACH, start=1):
        bot.send_message(CHAT_ID,f"⏳ Đang xử lý: {ma} → Đã hoàn thành: {int((chi_so-1)/tong_ma*100)}%")
        thanh_cong = lay_du_lieu_thanh_cong(ma)
        time.sleep(7) # nghỉ đủ tuân thủ quy tắc 5 lượt/phút tránh bị chặn
        if thanh_cong:
            bot.send_message(CHAT_ID,f"✅ Lấy thành công: {ma} → Tiến độ: {int(chi_so/tong_ma*100)}%")
        else:
            bot.send_message(CHAT_ID,f"⚠️ Tạm chưa lấy được dữ liệu {ma}, sẽ thử lại sau!")
    bot.send_message(CHAT_ID,f"🏁 **Kết thúc đợt: Tổng {len(ketqua_da_luu)}/{tong_ma} mã lấy đủ dữ liệu thành công!**")

# === LỆNH HIỂN THỊ ĐỦ THÔNG TIN CHÍNH XÁC ===
@bot.message_handler(func=lambda m:m.text.strip()=="Đánh giá mã")
def hien_thi_chi_tiet(m):
    if m.chat.id!=CHAT_ID: return
    if not ketqua_da_luu:
        bot.send_message(CHAT_ID,"🔍 Chưa có dữ liệu lưu sẵn → đang chạy thu thập báo % ngay bây giờ nhé!")
        chay_thu_thap()
        return
    bot.send_message(CHAT_ID,"📊 **BẢNG ĐÁNH GIÁ ĐỦ THÔNG TIN - THANG ĐIỂM 10**")
    # Sắp xếp ưu tiên điểm cao hiển thị trước
    for ma, thong_tin in sorted(ketqua_da_luu.items(), key=lambda x:x[1]["diem"], reverse=True):
        bot.send_message(CHAT_ID,f"""📌 **Mã: {ma}**
⭐ Tổng điểm: {thong_tin['diem']}/10 điểm
💵 Giá hiện tại tham khảo: {thong_tin['gia_hien']:,}đ
📈 Chỉ số RSI: {thong_tin['rsi']}
🎯 **Giá chốt lời mục tiêu**: {thong_tin['chot_loi']:,}đ
🛡️ **Giá bảo vệ vốn cắt lỗ**: {thong_tin['bao_von']:,}đ
💬 **Tín hiệu giao dịch**: {thong_tin['tin_hieu']}
——————————————————————""")

# === Khởi động ngay khi chạy bot ===
bot.send_message(CHAT_ID,"🤖✅ Đã sửa hoàn chỉnh: báo % tiến trình rõ ràng + đủ giá chốt lời, bảo vốn, tín hiệu đầu tư!")
chay_thu_thap()

# === Giữ bot sẵn sàng trả lời lệnh mọi lúc ===
while True:
    try: bot.polling(none_stop=True, interval=3)
    except Exception as e: time.sleep(5)
    time.sleep(1200) # nghỉ ngắn giữ kết nối ổn định, không làm mới liên tục quá nhanh
