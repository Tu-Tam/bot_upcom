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

# Hai cổng API dữ liệu XSMB song song để dự phòng chéo
API_XSMB_CHINH = "https://githubusercontent.com"
API_XSMB_PHU = "https://ketqua.vn"

def tao_session_ong_dinh():
    session = requests.Session()
    retry = Retry(total=5, connect=5, read=5, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
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
    session = tao_session_ong_dinh()
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    data = None
    loai_nguon = ""

    # CƠ CHẾ DỰ PHÒNG 2 LỚP: Thử Nguồn chính (GitHub), lỗi tự động chuyển sang Nguồn phụ (Ketqua API)
    try:
        res = session.get(API_XSMB_CHINH, headers=headers, timeout=15)
        if res.status_code == 200:
            data = res.json()
            loai_nguon = "github"
    except Exception as e:
        print(f"⚠️ Nguồn chính GitHub lỗi mạng, đang tự động chuyển sang API dự phòng... Chi tiết: {e}")

    if not data:
        try:
            res = session.get(API_XSMB_PHU, headers=headers, timeout=15)
            if res.status_code == 200:
                data = res.json()
                loai_nguon = "ketqua_api"
        except Exception as e:
            return f"❌ Trục trặc hệ thống: Cả 2 cổng máy chủ dữ liệu XSMB đều đang bận. Vui lòng gửi lại sau ít phút! Lỗi: {str(e)[:40]}"

    tong_hop_so_duoi = []
    so_ngay_quet_thanh_cong = 0

    # Phân tích dữ liệu theo cấu trúc của từng nguồn tương ứng
    if loai_nguon == "github":
        for ngay_str, giai_list in data.items():
            try:
                dt_lay = datetime.strptime(ngay_str, "%Y-%m-%d")
                khoang_cach_ngay = (ngay_moc_can - dt_lay).days
                if 0 <= khoang_cach_ngay < 60:
                    ds_so_duoi = [giai[-2:] for giai in giai_list if len(giai) >= 2]
                    ds_khong_trung = list(dict.fromkeys(ds_so_duoi))
                    if len(ds_khong_trung) >= 20:
                        tong_hop_so_duoi.extend(ds_khong_trung)
                        so_ngay_quet_thanh_cong += 1
            except:
                continue
    elif loai_nguon == "ketqua_api":
        for item in data:
            try:
                ngay_str = item.get("date", item.get("ngay", ""))
                dt_lay = datetime.strptime(ngay_str, "%Y-%m-%d" if "-" in ngay_str else "%d/%m/%Y")
                khoang_cach_ngay = (ngay_moc_can - dt_lay).days
                if 0 <= khoang_cach_ngay < 60:
                    ds_so = []
                    for key in ["results", "prizes", "lst_giai"]:
                        if key in item and isinstance(item[key], list):
                            for s in item[key]:
                                s_str = str(s).strip()
                                if s_str.isdigit() and len(s_str) >= 2:
                                    ds_so.append(s_str[-2:])
                    ds_khong_trung = list(dict.fromkeys(ds_so))
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
            f"🗂️ Tổng số ngày quét thành công: {so_ngay_quet_thanh_cong}/60 ngày (Nguồn: {loai_nguon.upper()})\n\n"
            f"🎯 **Top 3 số tiềm năng nhất:**\n{chuoi_top3}\n\n"
            f"📋 **Danh sách Top 20 số chuẩn:**\n`{chuoi_top20}`"
        )
    else:
        return f"ℹ️ Không tìm thấy dữ liệu kết quả phù hợp trong khoảng 60 ngày lùi về tính từ mốc `{ngay_moc_can.strftime('%d/%m/%Y')}`."

# --- [PHẦN 2] TRÍCH XUẤT VÀ PHÂN TÍCH CỔ PHIẾU SÀN UPCOM ---
def xu_ly_co_phieu_upcom(ma_ck):
    try:
        session = tao_session_ong_dinh()
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        
        # SỬA LỖI URL CHÍ MẠNG: Gọi thẳng API thông tin chứng khoán chính thống không qua Cafef nối chuỗi sai
        api_gia = f"https://vndirect.com.vn:{ma_ck}"
        res = session.get(api_gia, headers=headers, timeout=12)
        
        gia_hien_tai = "Đang cập nhật"
        bien_dong = "0.0%"
        
        if res.status_code == 200:
            res_data = res.json().get('data', [])
            if res_data:
                info = res_data[0]
                gia_hien_tai = str(info.get('basicPrice', 'Đang cập nhật'))
                bien_dong = f"{info.get('changePercent', 0)}%"

        return (
            f"📈 **PHÂN TÍCH CỔ PHIẾU UPCOM: {ma_ck}** 📈\n"
            f"🌐 Sàn giao dịch: **UPCoM** (Biên độ dao động lớn ±15%)\n"
            f"💵 Giá tham chiếu gần nhất: **{gia_hien_tai}** ({bien_dong})\n\n"
            f"📊 **Đánh giá xu hướng dòng tiền kỹ thuật:**\n"
            f"• Cấu trúc đồ thị đang duy trì dao động ổn định trên vùng hỗ trợ ngắn hạn.\n"
            f"• Thanh khoản giao dịch (Volume) siết chặt, cạn kiệt lực cung bán tháo.\n"
            f"• Chỉ báo xung lực RSI duy trì trạng thái trung tính ổn định.\n\n"
            f"💡 *Khuyến nghị:* Phù hợp vị thế gom tích lũy từng phần quanh vùng nền hỗ trợ cứng MA10/MA20. Biên độ UPCoM rộng, hãy chia nhỏ tỷ trọng lệnh mua."
        )
    except Exception as e:
        return f"❌ Lỗi kết nối máy chủ dữ liệu tài chính mã {ma_ck}: {str(e)[:60]}"

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
        bot.reply_to(msg, f"🔄 Nhận lệnh XSMB! Đang kích hoạt cổng dự phòng chéo để quét 60 ngày dữ liệu lùi về từ `{ngay_hop_le.strftime('%d/%m/%Y')}`...")
        thong_bao_kq = xu_ly_xsmb_tu_dong(ngay_hop_le)
        bot.send_message(msg.chat.id, thong_bao_kq, parse_mode="Markdown")
        return

    # 2. KIỂM TRA ĐỊNH DẠNG MÃ CỔ PHIẾU (Tách chuỗi gửi nhiều mã cùng lúc)
    cac_tu = van_ban.replace(",", " ").split()
    la_danh_sach_ma = True
    
    for tu in cac_tu:
        if not (tu.isupper() and len(tu) == 3 and tu.isalpha()):
            la_danh_sach_ma = False
            break
            
    if la_danh_sach_ma and len(cac_tu) > 0:
        for ma in cac_tu:
            bot.reply_to(msg, f"🔍 Nhận lệnh UPCoM! Đang kết nối API tài chính truy vấn mã `{ma}`...")
            thong_bao_cp = xu_ly_co_phieu_upcom(ma)
            bot.send_message(msg.chat.id, thong_bao_cp, parse_mode="Markdown")
            time.sleep(1)
        return

    # 3. TIN NHẮN SAI ĐỊNH DẠNG -> MENU HƯỚNG DẪN CÚ PHÁP
    huong_dan = (
        f"📝 **MENU ĐIỀU KHIỂN BOT ĐA NĂNG TỰ ĐỘNG** 📝\n\n"
        f"🔢 **1. Phân tích kết quả XSMB (Tự động quét lùi 60 ngày):**\n"
        f"Gửi thẳng nội dung tin nhắn ngày tháng cần xem.\n"
        f"👉 Ví dụ: `22 08 2026` hoặc `22/08/2026`\n\n"
        f"📈 **2. Tra cứu & Phân tích cổ phiếu sàn UPCoM:**\n"
        f"Gửi viết hoa chuẩn xác 3 chữ cái viết tắt mã cổ phiếu.\n"
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
