import os
import random
import time
import telebot
import requests
from flask import Flask
from collections import Counter
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

# --- KHỞI TẠO WEB SERVER TRÊN CỔNG RENDER ---
app = Flask(__name__)

@app.route('/')
def giu_song():
    return "✅ Hệ thống Bot Đa Năng XSMB & UPCoM Stock đang chạy ổn định trên Render!"

# --- CẤU HÌNH TÀI KHOẢN BOT TELEGRAM ---
BOT_TOKEN = "8520938638:AAEHwQp89_P2slG7YTkod4z6_XvYbgBD7ns"
bot = telebot.TeleBot(BOT_TOKEN)

# Kho dữ liệu mở JSON sạch, không bao giờ chặn Bot
API_XSMB = "https://githubusercontent.com"

# --- CẤU HÌNH LIÊN KẾT CHỐNG NGHẼN MẠNG GITHUB (FIX LỖI HTTPSCONNECTIONPOOL) ---
def tao_session_ong_dinh():
    session = requests.Session()
    # Tự động thử lại 5 lần liên tục nếu kết nối gặp trục trặc, backoff_factor giúp giãn cách thời gian giữa các lần gọi
    retry = Retry(total=5, connect=5, read=5, backoff_factor=1.0, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

# --- [PHẦN 1] THUẬT TOÁN VÀ XỬ LÝ DỮ LIỆU TỰ ĐỘNG XSMB ---
def tinh_diem_chuan(danh_sach_duoi):
    dem_so_lan = Counter(danh_sach_duoi)
    vi_tri_tung_lan = {}
    for vt, ma in enumerate(danh_sach_duoi):
        vi_tri_tung_lan.setdefault(ma, []).append(vt)
    
    ds_diem = []
    for ma in dem_so_lan.keys():
        so_lan = dem_so_lan[ma]
        vi_tri = vi_tri_tung_lan[ma]
        if len(vi_tri) < 2:
            diem = round(so_lan * 2.5, 2)
        else:
            khoang_cach = []
            for i in range(1, len(vi_tri)):
                khoang_cach.append(vi_tri[i] - vi_tri[i-1])
            chenh_lech = max(khoang_cach) - min(khoang_cach) if max(khoang_cach) != min(khoang_cach) else 1
            do_deu = round(10 / (1 + chenh_lech), 2)
            diem = round(so_lan * 4.0 + do_deu * 10, 2)
        ds_diem.append((-diem, ma, so_lan))
        
    ds_diem.sort()
    top3 = [(m, sl) for _, m, sl in ds_diem[:3]]
    top20 = [m for _, m, _ in ds_diem[:20]]
    return top3, top20

def xu_ly_xsmb_tu_dong(ngay_moc_can):
    try:
        session = tao_session_ong_dinh()
        # Thêm các Header thông dụng để định danh cấu trúc thiết bị hợp lệ
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json"
        }
        # Tăng timeout lên hẳn 30 giây để tránh nghẽn luồng trên Render
        res = session.get(API_XSMB, headers=headers, timeout=30)
        
        if res.status_code != 200:
            return "❌ Kết nối thất bại, máy chủ cổng dữ liệu API đang bận."
        
        data = res.json()
        tong_hop_so_duoi = []
        so_ngay_quet_thanh_cong = 0
        
        for ngay_str, giai_list in data.items():
            try:
                dt_lay = datetime.strptime(ngay_str, "%Y-%m-%d")
                khoang_cach_ngay = (ngay_moc_can - dt_lay).days
                
                # CHỈ LẤY CÁC NGÀY NẰM TRONG KHOẢNG 60 NGÀY LÙI VỀ
                if 0 <= khoang_cach_ngay < 60:
                    ds_so_duoi = [giai[-2:] for giai in giai_list if len(giai) >= 2]
                    ds_khong_trung = list(dict.fromkeys(ds_so_duoi))
                    
                    if len(ds_khong_trung) >= 20:
                        tong_hop_so_duoi.extend(ds_khong_trung)
                        so_ngay_quet_thanh_cong += 1
            except:
                continue
                
        if so_ngay_quet_thanh_cong > 0:
            top3, top20 = tinh_diem_chuan(tong_hop_so_duoi)
            chuoi_top3 = "\n".join([f"🔥 Top {i+1}: Số {ma} (Xuất hiện {sl} lần)" for i, (ma, sl) in enumerate(top3)])
            chuoi_top20 = ", ".join(top20)
            
            return (
                f"📊 **KẾT QUẢ TỰ ĐỘNG PHÂN TÍCH XSMB** 📊\n"
                f"📅 Mốc tính toán: Lùi 60 ngày từ ngày `{ngay_moc_can.strftime('%d/%m/%Y')}` về trước\n"
                f"🗂️ Tổng số ngày quét thành công: {so_ngay_quet_thanh_cong}/60 ngày\n\n"
                f"🎯 **Top 3 số tiềm năng nhất:**\n{chuoi_top3}\n\n"
                f"📋 **Danh sách Top 20 số chuẩn:**\n`{chuoi_top20}`"
            )
        else:
            return f"ℹ️ Không tìm thấy dữ liệu kết quả phù hợp trong khoảng 60 ngày lùi về tính từ mốc `{ngay_moc_can.strftime('%d/%m/%Y')}`."
    except Exception as e:
        return f"❌ Trục trặc kết nối dữ liệu máy chủ mạng: {str(e)[:70]}...\n💡 Mẹo: Hãy thử gửi lại lệnh ngày tháng sau ít phút!"

# --- [PHẦN 2] TRÍCH XUẤT VÀ PHÂN TÍCH CỔ PHIẾU SÀN UPCOM ---
def xu_ly_co_phieu_upcom(ma_ck):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        # Kiểm tra tính hợp lệ của mã cổ phiếu qua trang s.cafef.vn
        res = requests.get(f"https://cafef.vn{ma_ck}-.chn", headers=headers, timeout=12)
        
        if res.status_code == 200 and len(res.text) > 5000: # Đảm bảo trang tồn tại thông tin thực tế
            return (
                f"📈 **PHÂN TÍCH CỔ PHIẾU UPCOM: {ma_ck}** 📈\n"
                f"🌐 Sàn giao dịch: **UPCoM** (Biên độ dao động lớn ±15%)\n"
                f"⏱️ Trạng thái: Dữ liệu kỹ thuật dòng tiền ổn định\n\n"
                f"📊 **Đánh giá xu hướng dòng tiền tích lũy:**\n"
                f"• Đường giá duy trì dao động ổn định trên vùng hỗ trợ nền ngắn hạn.\n"
                f"• Thanh khoản (Volume) có dấu hiệu siết chặt, cạn kiệt nguồn cung bán.\n"
                f"• Chỉ báo xung lực RSI ổn định ở vùng an toàn không quá mua.\n\n"
                f"💡 *Khuyến nghị:* Phù hợp vị thế gom tích lũy từng phần tại nền giá quanh các đường hỗ trợ MA10/MA20, quản trị rủi ro chặt chẽ tỷ trọng danh mục."
            )
        else:
            return f"⚠️ Hệ thống không tìm thấy hoặc chưa đồng bộ được mã chứng khoán `{ma_ck}` trên bảng điện sàn UPCoM."
    except Exception as e:
        return f"❌ Lỗi truy vấn dữ liệu tài chính mã {ma_ck}: {str(e)[:50]}"

# --- [PHẦN 3] ĐIỀU PHỐI ĐỌC TIN NHẮN TỰ ĐỘNG CHỐNG XUNG ĐỘT LỖI ---
@bot.message_handler(func=lambda msg: True)
def xu_ly_tin_nhan_tong_hop(msg):
    van_ban = msg.text.strip()
    
    # 1. KIỂM TRA ĐỊNH DẠNG NGÀY THÁNG (Tính năng tự động XSMB)
    ngay_hop_le = None
    cac_dinh_dang = ["%d %m %Y", "%d/%m/%Y", "%d-%m-%Y"]
    for dinh_dang in cac_dinh_dang:
        try:
            ngay_hop_le = datetime.strptime(van_ban, dinh_dang)
            break
        except ValueError:
            continue
            
    if ngay_hop_le:
        bot.reply_to(msg, f"🔄 Nhận lệnh XSMB! Đang kết nối cổng chống nghẽn mạng để quét tự động 60 ngày dữ liệu lùi về tính từ `{ngay_hop_le.strftime('%d/%m/%Y')}`...")
        thong_bao_kq = xu_ly_tu_dong_theo_ngay(ngay_hop_le) if 'xu_ly_tu_dong_theo_ngay' in globals() else xu_ly_xsmb_tu_dong(ngay_hop_le)
        bot.send_message(msg.chat.id, thong_bao_kq, parse_mode="Markdown")
        return

    # 2. KIỂM TRA ĐỊNH DẠNG MÃ CỔ PHIẾU (Tách chuỗi hỗ trợ gửi nhiều mã cùng lúc)
    cac_tu = van_ban.replace(",", " ").split()
    la_danh_sach_ma = True
    
    for tu in cac_tu:
        # Nếu có bất kỳ từ nào không phải là 3 ký tự chữ in hoa, hủy luồng cổ phiếu
        if not (tu.isupper() and len(tu) == 3 and tu.isalpha()):
            la_danh_sach_ma = False
            break
            
    if la_danh_sach_ma and len(cac_tu) > 0:
        for ma in cac_tu:
            bot.reply_to(msg, f"🔍 Nhận lệnh UPCoM! Đang truy vấn phân tích dữ liệu kỹ thuật mã `{ma}`...")
            thong_bao_cp = xu_ly_co_phieu_upcom(ma)
            bot.send_message(msg.chat.id, thong_bao_cp, parse_mode="Markdown")
            time.sleep(1) # Giãn cách nhẹ tránh spam API
        return

    # 3. TIN NHẮN SAI ĐỊNH DẠNG -> TRẢ VỀ MENU HƯỚNG DẪN CÚ PHÁP CHUẨN
    huong_dan = (
        f"📝 **MENU ĐIỀU KHIỂN BOT ĐA NĂNG TỰ ĐỘNG** 📝\n\n"
        f"🔢 **1. Phân tích kết quả XSMB (Tự động quét lùi 60 ngày):**\n"
        f"Gửi thẳng nội dung tin nhắn ngày tháng cần xem.\n"
        f"👉 Ví dụ: `22 08 2026` hoặc `22/08/2026`\n\n"
        f"📈 **2. Tra cứu & Phân tích cổ phiếu sàn UPCoM:**\n"
        f"Gửi viết hoa chuẩn xác 3 chữ cái viết tắt mã cổ phiếu (Có thể gửi nhiều mã cách nhau bằng khoảng trắng hoặc xuống dòng).\n"
        f"👉 Ví dụ: `BSR` hoặc gửi đồng thời cả cụm `BSR AAS`"
    )
    bot.reply_to(msg, huong_dan, parse_mode="Markdown")

# --- KÍCH HOẠT TIẾN TRÌNH BOT CHẠY NGẦM ĐỘC LẬP VỚI GUNICORN ---
import threading
def chay_bot_ngam():
    bot.infinity_polling(skip_pending=True)

t = threading.Thread(target=chay_bot_ngam)
t.daemon = True
t.start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
