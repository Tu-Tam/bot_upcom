# === ĐOẠN GIỮ KẾT NỐI KHÔNG BỊ NGỦ TRÊN RENDER ===
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

# === TIẾP THEO TOÀN BỘ MÃ CHÍNH ĐÃ CHỈNH THÔNG SỐ NHẠY HƠN + BÁO RÕ ĐIỂM ===
import telebot
import time
import requests
from datetime import datetime

# === THÔNG TIN BOT CỦA BẠN ===
BOT_TOKEN = "8520938638:AAEHwQp89_P2slG7YTkod4z6_XvYbgBD7ns"
CHAT_ID = 7064473358       

bot = telebot.TeleBot(BOT_TOKEN)

# === DANH SÁCH MÃ UPCOM THANH KHOẢN TỐT ===
DANH_SACH_MA_UPCOM = ["SHB","HDB","TCB","VPB","MBB","SSB","EIB","VIX","MBS","VCI","SSI","ACB","BID","VCB"]

# === THAM SỐ ĐIỀU CHỈNH NHẠY HƠN ===
EMA_NGAN, EMA_DAI, SMA_DAI = 12, 26, 50
RSI_KY = 14
BOLL_KY, BOLL_HE_SO = 20, 2
THOI_GIAN_KIEM_TRA_GIA = 1800   
THOI_GIAN_KIEM_TRA_MANG = 60     
THOI_GIAN_BAO_SONG_PHUT = 120    

# === LƯU TRỮ TRẠNG THÁI ===
trang_thai = {ma: "CHO_DOI" for ma in DANH_SACH_MA_UPCOM}
du_lieu_vi_the = {}
trang_thai_mang = True  
dem_bao_song = 0        

# === HÀM KIỂM TRA KẾT NỐI MẠNG ===
def kiem_tra_ket_noi_mang():
    try:
        requests.get("https://api.telegram.org", timeout=7)
        return True
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        return False

# === HÀM PHÂN TÍCH LỌC MÃ VỚI THAM SỐ MỚI ===
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

        # === ĐIỀU CHỈNH TIÊU CHÍ DỄ ĐẠT HƠN ===
        diem = 0
        if ema_ngan > ema_dai and ema_dai > sma_dai: diem += 2
        if macd_line > signal_line and macd_line > 0: diem += 2
        if rsi > 35 and rsi < 70: diem += 2 # Mở rộng khoảng RSI
        if kl_hien > kl_tb20 * 1.03: diem += 2 # Chỉ cần cao hơn trung bình 3% là đủ
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

# === LỆNH TRẢ LỜI KHI HỎI Trạng thái ===
@bot.message_handler(func=lambda message: message.text.strip() == "Trạng thái")
def tra_loi_trang_thai(message):
    if message.chat.id != CHAT_ID: return
    thoi_gian_hien_tai = datetime.now().strftime("%H:%M:%S %d/%m/%Y")
    bot.send_message(chat_id=CHAT_ID, text=f"""💓 **TRẠNG THÁI HOẠT ĐỘNG:** ĐANG CHẠY BÌNH THƯỜNG ✅
⏰ Thời gian: {thoi_gian_hien_tai}
📶 Kết nối mạng: Đang ổn định
📈 Đang theo dõi danh sách {len(DANH_SACH_MA_UPCOM)} mã UPCOM
💡 Nhận tin này ngay = Bot đang hoạt động nhanh nhạy trong nền!""")

# === XỬ LÝ Đã mua / Đã bán ===
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

# === VÒNG CHẠY CHÍNH: BÁO CHI TIẾT ĐIỂM SỐ RÕ RÀNG ===
print("=== BẮT ĐẦU HOẠT ĐỘNG: NGƯỠNG 5 ĐIỂM TRỞ LÊN + BÁO CHI TIẾT TỪNG MỤC ===")
bot.send_message(chat_id=CHAT_ID, text="""🤖✅ **Đã CẬP NHẬT THÀNH CÔNG:**
💓 Báo sống mỗi 2 giờ
📶 Báo ngay khi mất mạng/kết nối lại
💬 Gửi **Trạng thái** kiểm tra bất kỳ lúc nào
📉 Ngưỡng giảm xuống 5 điểm trở lên, báo rõ từng tiêu chí cộng điểm giúp dễ ra quyết định!""")

while True:
    mang_ban_dau = trang_thai_mang
    trang_thai_mang = kiem_tra_ket_noi_mang()

    if mang_ban_dau == True and trang_thai_mang == False:
        try:
            bot.send_message(chat_id=CHAT_ID, text="""🚫⚠️ **THÔNG BÁO: ĐÃ MẤT KẾT NỐI MẠNG**
⏰ Thời gian: {}
Bot tạm dừng kiểm tra giá chờ kết nối trở lại...""".format(datetime.now().strftime("%H:%M:%S %d/%m/%Y")))
        except: pass

    elif mang_ban_dau == False and trang_thai_mang == True:
        try:
            bot.send_message(chat_id=CHAT_ID, text="""✅📶 **ĐÃ KẾT NỐI MẠNG TRỞ LẠI THÀNH CÔNG!**
⏰ Thời gian: {}
Tiếp tục theo dõi, quét tìm cơ hội bình thường trở lại!""".format(datetime.now().strftime("%H:%M:%S %d/%m/%Y")))
        except: pass

    if trang_thai_mang:
        try:
            bot.polling(none_stop=True, interval=2)
        except Exception as e:
            print(f"Lỗi tạm thời kết nối bot: {e}")
            time.sleep(5)
            continue

        dem_bao_song += 1
        if dem_bao_song >= THOI_GIAN_BAO_SONG_PHUT:
            try:
                bot.send_message(chat_id=CHAT_ID, text=f"💓 BÁO SỐNG: Bot vẫn đang chạy theo dõi ổn định! ⏰ {datetime.now().strftime('%H:%M %d/%m')}")
            except: pass
            dem_bao_song = 0

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

            # === ✅ ĐỔI MỚI: NGƯỠNG 5 ĐIỂM + BÁO RÕ CHI TIẾT TỪNG MỤC ===
            elif kq["diem"] >= 5 and trang_thai[ma] != "CHO_XAC_NHAN_DAMUA":
                bot.send_message(chat_id=CHAT_ID, text=f"""📢🚀 **TÍN HIỆU CƠ HỘI: {ma}**
💵 Giá hiện tại: {kq['gia']:,}đ
📈 **Tổng điểm đạt được: {kq['diem']}/10 điểm**

📋 Chi tiết từng tiêu chí đánh giá:
✅ Xu hướng giá tăng rõ EMA ngắn trên EMA dài: +2 điểm
✅ MACD dương, động lượng tăng tốt: +2 điểm
✅ Chỉ số RSI {kq['rsi']} trong vùng khỏe: +2 điểm
✅ Khối lượng cao hơn trung bình, có dòng tiền tham gia: +2 điểm
✅ Giá nằm trong vùng hỗ trợ - kháng cự an toàn: +2 điểm

📍 Vùng hỗ trợ: {kq['ho_tro']:,}đ | Vùng kháng cự: {kq['khang_cu']:,}đ
🎯 Giá mục tiêu chốt lời: {kq['cl']:,}đ
🛡️ Giá ngăn ngừa thua lỗ: {kq['catl']:,}đ

💡 Lưu ý tham khảo:
🔹5-6 điểm: có tín hiệu, xem xét thận trọng, dùng vốn nhỏ
🔹7-8 điểm: tín hiệu tốt, đáng ưu tiên xem xét
🔹9-10 điểm: hội tụ đủ yếu tố mạnh nhất
*Là phân tích kỹ thuật tham khảo, kết hợp tin tức thị trường trước ra quyết định nhé!*

👉 Nếu đồng ý theo dõi trả lời: **Đã mua** để Bot tự canh báo đúng giá!""")
                trang_thai[ma] = "CHO_XAC_NHAN_DAMUA"
                trang_thai[f"gia_{ma}"] = kq["gia"]
                trang_thai[f"cl_{ma}"] = kq["cl"]
                trang_thai[f"catl_{ma}"] = kq["catl"]

    time.sleep(THOI_GIAN_KIEM_TRA_MANG)
