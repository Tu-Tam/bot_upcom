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

# === TOÀN BỘ MÃ CHÍNH ĐỦ THÔNG TIN ĐIỂM + GIÁ MỤC TIÊU ===
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
du_lieu_diem_gan_nhat = {} # Lưu đủ điểm + giá + chốt lời + cắt lỗ
trang_thai_mang = True  
dem_bao_song = 0        

# === HÀM KIỂM TRA KẾT NỐI MẠNG ===
def kiem_tra_ket_noi_mang():
    try:
        requests.get("https://api.telegram.org", timeout=7)
        return True
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        return False

# === HÀM PHÂN TÍCH LẤY ĐỦ THÔNG SỐ ===
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

        # === Tính điểm theo thang 10 ===
        diem = 0
        if ema_ngan > ema_dai and ema_dai > sma_dai: diem += 2
        if macd_line > signal_line and macd_line > 0: diem += 2
        if rsi > 35 and rsi < 70: diem += 2
        if kl_hien > kl_tb20 * 1.03: diem += 2
        if gia_hien_tai > ho_tro and gia_hien_tai < khang_cu and gia_hien_tai < boll_tren: diem += 2

        gia_cl = round(min(khang_cu, boll_tren) * 0.995, 2) # Giá chốt lời
        gia_cat = round(min(ho_tro, boll_duoi) * 0.995, 2) # Giá bảo vệ vốn

        ket_qua = {
            "gia": gia_hien_tai, "diem": diem, "rsi": rsi,
            "cl": gia_cl, "catl": gia_cat
        }
        du_lieu_diem_gan_nhat[ma] = ket_qua
        return ket_qua
    except Exception as e:
        print(f"Lỗi phân tích {ma}: {e}")
        return None

# === LỆNH TRẠNG THÁI ===
@bot.message_handler(func=lambda message: message.text.strip() == "Trạng thái")
def tra_loi_trang_thai(message):
    if message.chat.id != CHAT_ID: return
    thoi_gian_hien_tai = datetime.now().strftime("%H:%M:%S %d/%m/%Y")
    bot.send_message(chat_id=CHAT_ID, text=f"""💓 **TRẠNG THÁI HOẠT ĐỘNG:** ĐANG CHẠY BÌNH THƯỜNG ✅
⏰ Thời gian: {thoi_gian_hien_tai}
📶 Kết nối mạng: Đang ổn định
📈 Đang theo dõi danh sách {len(DANH_SACH_MA_UPCOM)} mã UPCOM
💬 Gõ: **Đánh giá mã** → xem điểm + giá + chốt lời + bảo vệ vốn rõ ràng!""")

# === ✅ LỆNH ĐÁNH GIÁ: Điểm 10 + Nhận xét + Giá hiện tại + Chốt lời + Cắt lỗ ===
@bot.message_handler(func=lambda message: message.text.strip() == "Đánh giá mã")
def xem_diem_tat_ca(message):
    if message.chat.id != CHAT_ID: return
    if not du_lieu_diem_gan_nhat:
        bot.send_message(chat_id=CHAT_ID, text="⏳ Đang tính dữ liệu giá, vui lòng chờ ít phút thử lại nhé!")
        return
    bot.send_message(chat_id=CHAT_ID, text="📊 **BẢNG ĐÁNH GIÁ CHI TIẾT (Thang điểm 10)**\n")
    noi_dung = ""
    for ma, tt in du_lieu_diem_gan_nhat.items():
        d = tt["diem"]
        # Nhận xét rõ mức
        if d >= 7:
            xep_hang = "⭐ TỐT: nhiều yếu tố đồng bộ, cơ hội tăng giá rõ rệt ưu tiên xem xét"
        elif d >= 5:
            xep_hang = "🔸 TRUNG BÌNH: có tín hiệu nhẹ, theo dõi thêm, cân nhắc vốn nhỏ"
        else:
            xep_hang = "🔹 YẾU: chưa đủ tiêu chí tốt, tạm theo dõi chờ cải thiện thêm"

        noi_dung += f"""📌 **{ma}**: {d}/10 điểm
💵 Giá hiện tại: {tt['gia']:,}đ
🎯 Giá chốt lời mục tiêu: {tt['cl']:,}đ
🛡️ Giá bảo vệ vốn an toàn: {tt['catl']:,}đ
📝 Nhận xét: {xep_hang}
——————————————————\n"""

    bot.send_message(chat_id=CHAT_ID, text=noi_dung)

# === XỬ LÝ Đã mua / Đã báo khi chạm giá đúng mức ===
@bot.message_handler(func=lambda message: message.text.strip() == "Đã mua")
def da_mua(message):
    if message.chat.id != CHAT_ID: return
    for ma in DANH_SACH_MA_UPCOM:
        if trang_thai[ma] == "CHO_XAC_NHAN_DAMUA":
            du_lieu_vi_the[ma] = {
                "gia_vao": trang_thai[f"gia_{ma}"],
                "cl": trang_thai[f"cl_{ma}"],
                "catl": trang_thai[f"catl_{ma}"]
            }
            trang_thai[ma] = "DANG_NAM_GIU"
            bot.send_message(chat_id=CHAT_ID, text=f"""✅ Ghi nhận theo dõi: {ma}
💵 Giá vào lệnh: {du_lieu_vi_the[ma]['gia_vao']:,}đ
🎯 Chốt lời: {du_lieu_vi_the[ma]['cl']:,}đ
🛡️ Cắt lỗ bảo vốn: {du_lieu_vi_the[ma]['catl']:,}đ""")
            return
    bot.send_message(chat_id=CHAT_ID, text="⚠️ Chờ tín hiệu cơ hội tiếp theo nhé!")

@bot.message_handler(func=lambda message: message.text.strip() == "Đã bán")
def da_ban(message):
    if message.chat.id != CHAT_ID: return
    for ma in DANH_SACH_MA_UPCOM:
        if trang_thai[ma] == "DANG_NAM_GIU" and ma in du_lieu_vi_the:
            del du_lieu_vi_the[ma]
            trang_thai[ma] = "CHO_DOI"
            bot.send_message(chat_id=CHAT_ID, text=f"""🔄✅ Đã kết thúc theo dõi {ma}!""")
            return
    bot.send_message(chat_id=CHAT_ID, text="⚠️ Đang theo dõi tín hiệu nhé!")

# === VÒNG CHẠY CHÍNH ===
print("=== Đã cập nhật: Đánh giá đủ điểm + nhận xét + giá chốt lời/bảo vốn ===")
bot.send_message(chat_id=CHAT_ID, text="""🤖✅ **SẴN SÀNG HOÀN HẢO:**
💬 Gõ **Đánh giá mã** xem ngay: ✅Điểm/10 ✅Nhận xét ✅Giá hiện tại ✅Giá chốt lời ✅Giá bảo vệ vốn đủ thông tin ra quyết định!""")

while True:
    mang_ban_dau = trang_thai_mang
    trang_thai_mang = kiem_tra_ket_noi_mang()

    if mang_ban_dau == True and trang_thai_mang == False:
        try: bot.send_message(chat_id=CHAT_ID, text="🚫⚠️ Mất kết nối mạng tạm thời!")
        except: pass
    elif mang_ban_dau == False and trang_thai_mang == True:
        try: bot.send_message(chat_id=CHAT_ID, text="✅📶 Kết nối mạng trở lại, tiếp tục theo dõi bình thường!")
        except: pass

    if trang_thai_mang:
        try: bot.polling(none_stop=True, interval=2)
        except Exception as e: print(f"Lỗi kết nối: {e}"); time.sleep(5); continue

        dem_bao_song += 1
        if dem_bao_song >= THOI_GIAN_BAO_SONG_PHUT:
            try: bot.send_message(chat_id=CHAT_ID, text=f"💓 BÁO SỐNG: Bot vẫn chạy ổn định! ⏰ {datetime.now().strftime('%H:%M %d/%m')}")
            except: pass
            dem_bao_song = 0

        for ma in DANH_SACH_MA_UPCOM:
            kq = phan_tich_tu_dong(ma)
            if not kq: continue

            if trang_thai[ma] == "DANG_NAM_GIU":
                vt = du_lieu_vi_the[ma]
                if kq["gia"] >= vt["cl"]:
                    bot.send_message(chat_id=CHAT_ID, text=f"🏆✅ ĐẠT MỤC TIÊU THU LỢI: {ma}\nGiá {kq['gia']:,}đ đã đạt mức chốt lời {vt['cl']:,}đ\n👉 Trả lời **Đã bán** nhé!")
                    continue
                if kq["gia"] <= vt["catl"]:
                    bot.send_message(chat_id=CHAT_ID, text=f"🛑⚠️ BẢO VỆ VỐN CẮT LỖ: {ma}\nGiá {kq['gia']:,}đ chạm ngưỡng an toàn {vt['catl']:,}đ\n👉 Thoát lệnh theo kế hoạch rồi trả lời **Đã bán** nhé!")
                    continue

            elif kq["diem"] >= 5 and trang_thai[ma] != "CHO_XAC_NHAN_DAMUA":
                bot.send_message(chat_id=CHAT_ID, text=f"""📢🚀 **TÍN HIỆU CƠ HỘI: {ma}**
💵 Giá hiện tại: {kq['gia']:,}đ
📈 Tổng điểm đạt được: {kq['diem']}/10 điểm
🎯 Giá chốt lời mục tiêu: {kq['cl']:,}đ
🛡️ Giá bảo vệ vốn an toàn: {kq['catl']:,}đ
📝 Nhận xét: có tín hiệu tốt, đủ ngưỡng xem xét
👉 Trả lời **Đã mua** để ghi nhận theo dõi chặt chẽ giá nhé!""")
                trang_thai[ma] = "CHO_XAC_NHAN_DAMUA"
                trang_thai[f"gia_{ma}"] = kq["gia"]
                trang_thai[f"cl_{ma}"] = kq["cl"]
                trang_thai[f"catl_{ma}"] = kq["catl"]

    time.sleep(THOI_GIAN_KIEM_TRA_MANG)
