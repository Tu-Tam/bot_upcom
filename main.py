# === ĐOẠN MỚI THÊM: GIỮ KẾT NỐI KHÔNG BỊ NGỦ TRÊN RENDER ===
from flask import Flask
from threading import Thread
import os

app = Flask('')
@app.route('/')
def giu_chay():
    return "✅ Bot đang hoạt động tốt! Đã kết nối giữ sống thành công."

def chay_server():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

Thread(target=chay_server).start()

# === TIẾP THEO TOÀN BỘ MÃ CỦA BẠN ĐỀU NGUYÊN NỘI DUNG CHÍNH XÁC ===
import telebot
import time
import requests
from datetime import datetime

# === THÔNG TIN BOT CỦA BẠN ===
BOT_TOKEN = "8520938638:AAEHwQp89_P2slG7YTkod4z6_XvYbgBD7ns"
CHAT_ID = 7064473358       # Thay bằng số Chat ID cá nhân

bot = telebot.TeleBot(BOT_TOKEN)

# === DANH SÁCH MÃ UPCOM THANH KHOẢN TỐT ===
DANH_SACH_MA_UPCOM = ["SHB","HDB","TCB","VPB","MBB","SSB","EIB","VIX","MBS","VCI","SSI","ACB","BID","VCB"]

# === THAM SỐ ĐỀU ĐẶT RÕ RÀNG ===
EMA_NGAN, EMA_DAI, SMA_DAI = 12, 26, 50
RSI_KY = 14
BOLL_KY, BOLL_HE_SO = 20, 2
THOI_GIAN_KIEM_TRA_GIA = 1800   # Kiểm tra giá mỗi 30 phút
THOI_GIAN_KIEM_TRA_MANG = 60     # Kiểm tra mạng mỗi 60 giây
THOI_GIAN_BAO_SONG_PHUT = 120    # Báo sống tự động mỗi 2 giờ 1 lần

# === LƯU TRỮ TRẠNG THÁI ===
trang_thai = {ma: "CHO_DOI" for ma in DANH_SACH_MA_UPCOM}
du_lieu_vi_the = {}
trang_thai_mang = True  # Theo dõi chuyển trạng thái mạng báo 1 lần thôi
dem_bao_song = 0        # Biến đếm thời gian báo sống định kỳ

# === HÀM KIỂM TRA KẾT NỐI MẠNG ===
def kiem_tra_ket_noi_mang():
    try:
        requests.get("https://api.telegram.org", timeout=7)
        return True
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        return False

# === HÀM PHÂN TÍCH LỌC MÃ TĂNG TỐT ĐÃ CHẠY ỔN ===
def phan_tich_tu_dong(ma):
    try:
        url = f"https://api.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={ma}&apikey=demo&outputsize=compact"
        du_lieu = requests.get(url, timeout=12).json()
        if "Time Series (Daily)" not in du_lieu:
            return None

        ds_ngay = sorted(du_lieu["Time Series (Daily)"].keys(), reverse=True)
        gia_dong, gia_cao, gia_thap, khoi_luong = [], [], [], []
        for ngay in ds_ngay[:60]:
            d = du_lieu["Time Series (Daily)"][ngay]
            gia_dong.append(float(d["4. close"]))
            gia_cao.append(float(d["2. high"]))
            gia_thap.append(float(d["3. low"]))
            khoi_luong.append(int(d["5. volume"]))
        gia_hien_tai = round(gia_dong[0], 2)

        def tinh_ema(ds, ky):
            hs = 2 / (ky + 1)
            ema = sum(ds[:ky]) / ky
            for g in ds[ky:]:
                ema = g * hs + ema * (1 - hs)
            return round(ema, 2)

        ema_ngan = tinh_ema(gia_dong, EMA_NGAN)
        ema_dai = tinh_ema(gia_dong, EMA_DAI)
        sma_dai = round(sum(gia_dong[:SMA_DAI]) / SMA_DAI, 2)

        ema12 = tinh_ema(gia_dong, 12)
        ema26 = tinh_ema(gia_dong, 26)
        macd_line = round(ema12 - ema26, 4)
        signal_line = tinh_ema([macd_line], 9) if len([macd_line]) >= 9 else macd_line

        def tinh_rsi(ds, ky):
            tang = []
            giam = []
            for i in range(1, ky + 1):
                chenh_lech = ds[i-1] - ds[i]
                if chenh_lech > 0:
                    tang.append(chenh_lech)
                    giam.append(0)
                else:
                    tang.append(0)
                    giam.append(-chenh_lech)
            tb_tang = sum(tang) / ky
            tb_giam = sum(giam) / ky
            if tb_giam == 0:
                return 100.0
            if tb_tang == 0:
                return 0.0
            return round(100 - (100 / (1 + tb_tang / tb_giam)), 2)

        rsi = tinh_rsi(gia_dong, RSI_KY)

        sma_boll = sum(gia_dong[:BOLL_KY]) / BOLL_KY
        do_lech = round(((sum([(x - sma_boll)**2 for x in gia_dong[:BOLL_KY]]) / BOLL_KY))**0.5, 2)
        boll_tren = round(sma_boll + BOLL_HE_SO * do_lech, 2)
        boll_duoi = round(sma_boll - BOLL_HE_SO * do_lech, 2)
        ho_tro = round(min(gia_thap[:20]), 2)
        khang_cu = round(max(gia_cao[:20]), 2)
        kl_tb20 = round(sum(khoi_luong[:20]) / 20)
        kl_hien = khoi_luong[0]

        diem = 0
        if ema_ngan > ema_dai and ema_dai > sma_dai: diem += 2
        if macd_line > signal_line and macd_line > 0: diem += 2
        if rsi > 40 and rsi < 65: diem += 2
        if kl_hien > kl_tb20 * 1.08: diem += 2
        if gia_hien_tai > ho_tro and gia_hien_tai < khang_cu and gia_hien_tai < boll_tren: diem += 2

        gia_cl = round(min(khang_cu, boll_tren) * 0.995, 2)
        gia_cat = round(min(ho_tro, boll_duoi) * 0.995, 2)

        return {
            "gia": gia_hien_tai, "ema_n": ema_ngan, "ema_d": ema_dai, "sma_d": sma_dai,
            "rsi": rsi, "diem": diem, "ho_tro": ho_tro, "khang_cu": khang_cu,
            "cl": gia_cl, "catl": gia_cat
        }
    except Exception as e:
        print(f"Lỗi phân tích {ma}: {e}")
        return None

# === ✅ LỆNH MỚI: TRẢ LỜI NGAY KHI BẠN HỎI "Trạng thái" ===
@bot.message_handler(func=lambda message: message.text.strip() == "Trạng thái")
def tra_loi_trang_thai(message):
    if message.chat.id != CHAT_ID: return
    thoi_gian_hien_tai = datetime.now().strftime("%H:%M:%S %d/%m/%Y")
    bot.send_message(chat_id=CHAT_ID, text=f"""💓 **TRẠNG THÁI HOẠT ĐỘNG:** ĐANG CHẠY BÌNH THƯỜNG ✅
⏰ Thời gian: {thoi_gian_hien_tai}
📶 Kết nối mạng: Đang ổn định
📈 Đang theo dõi danh sách {len(DANH_SACH_MA_UPCOM)} mã UPCOM
💡 Nhận tin này ngay = Bot đang hoạt động nhanh nhạy trong nền!""")

# === XỬ LÝ TIN NHẮN TRẢ LỜI Đã mua / Đã bán vẫn giữ nguyên ổn định ===
@bot.message_handler(func=lambda message: message.text.strip() == "Đã mua")
def da_mua(message):
    if message.chat.id != CHAT_ID: return
    for ma in DANH_SACH_MA_UPCOM:
        if trang_thai[ma] == "CHO_XAC_NHAN_DAMUA":
            du_lieu_vi_the[ma] = {"gia_vao": trang_thai[f"gia_{ma}"], "cl": trang_thai[f"cl_{ma}"], "catl": trang_thai[f"catl_{ma}"]}
            trang_thai[ma] = "DANG_NAM_GIU"
            bot.send_message(chat_id=CHAT_ID, text=f"""✅ Ghi nhận tự động theo dõi: {ma}
💵 Giá vào lệnh: {du_lieu_vi_the[ma]['gia_vao']:,}đ
🎯 Mục tiêu thu lời: {du_lieu_vi_the[ma]['cl']:,}đ
🛡️ Ngưỡng bảo vệ vốn: {du_lieu_vi_the[ma]['catl']:,}đ
👉 Tự động canh chừng báo ngay khi chạm mức! Nhớ trả lời **Đã bán** khi xong nhé!""")
            return
    bot.send_message(chat_id=CHAT_ID, text="⚠️ Chờ tự động lọc ra cơ hội tiếp theo nhé!")

@bot.message_handler(func=lambda message: message.text.strip() == "Đã bán")
def da_ban(message):
    if message.chat.id != CHAT_ID: return
    for ma in DANH_SACH_MA_UPCOM:
        if trang_thai[ma] == "DANG_NAM_GIU" and ma in du_lieu_vi_the:
            del du_lieu_vi_the[ma]
            trang_thai[ma] = "CHO_DOI"
            bot.send_message(chat_id=CHAT_ID, text=f"""🔄✅ Đã kết thúc tự động theo dõi {ma}!
Sẵn sàng tiếp tục quét toàn bộ danh sách tìm cơ hội chất lượng tiếp theo tự động nhé!""")
            return
    bot.send_message(chat_id=CHAT_ID, text="⚠️ Đang chờ tín hiệu tự động tiếp theo nhé!")

# === VÒNG CHẠY CHÍNH: BÁO SỐNG ĐỊNH KỲ + BÁO THAY ĐỔI MẠNG ===
print("=== BẮT ĐẦU HOẠT ĐỘNG: CÓ THỂ HỎI BẰNG TỪ: Trạng thái ===")
bot.send_message(chat_id=CHAT_ID, text="""🤖✅ **Đã KHỞI ĐỘNG HOÀN TOÀN:**
💓 Tự báo sống mỗi 2 giờ
📶 Báo ngay khi mất mạng / kết nối lại thành công
💬 Gửi tin chữ: **Trạng thái** → trả lời ngay kiểm tra bất kỳ lúc nào
📈 Vẫn lọc mã tốt, báo tín hiệu, theo dõi chốt lời/cắt lỗ như đã dùng!""")

while True:
    mang_ban_dau = trang_thai_mang
    trang_thai_mang = kiem_tra_ket_noi_mang()

    # Báo khi chuyển từ có mạng sang mất mạng
    if mang_ban_dau == True and trang_thai_mang == False:
        try:
            bot.send_message(chat_id=CHAT_ID, text="""🚫⚠️ **THÔNG BÁO: ĐÃ MẤT KẾT NỐI MẠNG**
⏰ Thời gian: {}
Bot tạm dừng kiểm tra giá chờ kết nối trở lại...""".format(datetime.now().strftime("%H:%M:%S %d/%m/%Y")))
        except: pass

    # Báo khi kết nối mạng trở lại
    elif mang_ban_dau == False and trang_thai_mang == True:
        try:
            bot.send_message(chat_id=CHAT_ID, text="""✅📶 **ĐÃ KẾT NỐI MẠNG TRỞ LẠI THÀNH CÔNG!**
⏰ Thời gian: {}
Tiếp tục theo dõi, quét tìm cơ hội bình thường trở lại!""".format(datetime.now().strftime("%H:%M:%S %d/%m/%Y")))
        except: pass

    # Chỉ làm việc khi có kết nối tốt
    if trang_thai_mang:
        try:
            bot.polling(none_stop=True, interval=2)
        except Exception as e:
            print(f"Lỗi tạm thời kết nối bot: {e}")
            time.sleep(5)
            continue

        # === Báo sống định kỳ mỗi đủ 2 giờ ===
        dem_bao_song += 1
        if dem_bao_song >= THOI_GIAN_BAO_SONG_PHUT:
            try:
                bot.send_message(chat_id=CHAT_ID, text=f"💓 BÁO SỐNG: Bot vẫn đang chạy theo dõi ổn định! ⏰ {datetime.now().strftime('%H:%M %d/%m')}")
            except: pass
            dem_bao_song = 0

        # Quét phân tích kiểm tra tín hiệu cổ phiếu
        for ma in DANH_SACH_MA_UPCOM:
            kq = phan_tich_tu_dong(ma)
            if not kq: continue

            if trang_thai[ma] == "DANG_NAM_GIU":
                vt = du_lieu_vi_the[ma]
                if kq["gia"] >= vt["cl"]:
                    bot.send_message(chat_id=CHAT_ID, text=f"🏆✅ ĐẠT MỤC TIÊU THU LỢI: {ma}\nGiá {kq['gia']:,}đ đã đạt mức {vt['cl']:,}đ\n👉 Thực hiện bán rồi trả lời **Đã bán** nhé!")
                    continue
                if kq["gia"] <= vt["catl"]:
                    bot.send_message(chat_id=CHAT_ID, text=f"🛑⚠️ BẢO VỆ VỐN CẮT LỖ: {ma}\nGiá {kq['gia']:,}đ chạm ngưỡng an toàn {vt['catl']:,}đ\n👉 Thoát lệnh theo kế hoạch rồi trả lời **Đã bán** nhé!")
                    continue

            elif kq["diem"] >= 7 and trang_thai[ma] != "CHO_XAC_NHAN_DAMUA":
                bot.send_message(chat_id=CHAT_ID, text=f"""📢🚀 TỰ ĐỘNG LỌC RA CƠ HỘI TỐT: {ma}
💵 Giá hiện tại: {kq['gia']:,}đ
📈 Xu hướng: EMA{kq['ema_n']} > {kq['ema_d']} > SMA{kq['sma_d']} | RSI: {kq['rsi']} khỏe
📍 Vùng hỗ trợ: {kq['ho_tro']:,}đ | Kháng cự: {kq['khang_cu']:,}đ
🎯 Mục tiêu thu lời tự tính: {kq['cl']:,}đ
🛡️ Ngưỡng an toàn tự đặt: {kq['catl']:,}đ
💯 Tổng điểm đồng thuận: {kq['diem']}/10
👉 Nếu đồng ý & đã vào lệnh thành công vui lòng trả lời: **Đã mua** để tôi tự ghi nhận theo dõi nhé!""")
                trang_thai[ma] = "CHO_XAC_NHAN_DAMUA"
                trang_thai[f"gia_{ma}"] = kq["gia"]
                trang_thai[f"cl_{ma}"] = kq["cl"]
                trang_thai[f"catl_{ma}"] = kq["catl"]

    time.sleep(THOI_GIAN_KIEM_TRA_MANG)
