# === MÃ NGUỒN BOT TELEGRAM: TỰ ĐỘNG CẬP NHẬT QUA CỔNG API JSON CHỐNG CHẶN ===
import os
import random
from flask import Flask
from threading import Thread
import time
import telebot
import requests
from collections import Counter
from datetime import datetime

# --- Khởi tạo Web Server giữ song song (Tối ưu cho Render/Heroku) ---
app = Flask(__name__)
@app.route('/')
def giu_song():
    return "✅ Hệ thống kết nối cổng API JSON đang hoạt động ổn định!"

def chay_server():
    # Sử dụng cổng PORT do môi trường cấu hình hoặc mặc định 8080
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

Thread(target=chay_server).start()

# --- Cấu hình Tài khoản Bot & Người nhận ---
BOT_TOKEN = "8520938638:AAEHwQp89_P2slG7YTkod4z6_XvYbgBD7ns"
CHAT_ID = 7064473358
bot = telebot.TeleBot(BOT_TOKEN)

# Bộ nhớ đệm lưu trữ dữ liệu tính toán (Cộng dồn vĩnh viễn không tự xóa)
DA_CO_DU_LIEU = {}

# Định nghĩa cổng API sạch từ kho lưu trữ mở không bao giờ chặn bot
DANH_SACH_NGUON_UU_TIEN = [
    {
        "ten": "Kho dữ liệu mở XSMB (GitHub API)", 
        "link": "https://githubusercontent.com"
    }
]

# --- Hàm xử lý thuật toán phân tích điểm chuẩn ---
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

# --- Hàm gọi API lấy dữ liệu tự động (Thay thế hoàn toàn bộ cào HTML cũ) ---
def lay_tu_trang_tonghop(link, ngay_moc_can):
    tap_moi_lay_duoc = {}
    try:
        # Gọi trực tiếp file JSON thô từ GitHub, loại bỏ hoàn toàn việc phân tích HTML
        res = requests.get(link, timeout=15)
        if res.status_code != 200: 
            return {}
        
        # Parse dữ liệu dạng JSON: {"YYYY-MM-DD": ["giải 1", "giải 2", ...]}
        data = res.json()
        
        for ngay_str, giai_list in data.items():
            try:
                # Chuyển đổi định dạng ngày từ JSON sang datetime object
                dt_lay = datetime.strptime(ngay_str, "%Y-%m-%d")
                chuoi_ngay_chuan = dt_lay.strftime("%d/%m/%Y")
                
                # Kiểm tra điều kiện khoảng cách ngày (nằm trong giới hạn 60 ngày gần nhất)
                so_ngay_ke = (ngay_moc_can - dt_lay).days
                if not (0 <= so_ngay_ke < 60): 
                    continue
                
                # Trích xuất 2 chữ số cuối (loto đầu đuôi) từ danh sách các giải
                ds_so = [giai[-2:] for giai in giai_list if len(giai) >= 2]
                ds_khong_trung = list(dict.fromkeys(ds_so))
                
                # Nếu một ngày có đủ bộ kết quả tin cậy, lưu vào tập dữ liệu mới
                if len(ds_khong_trung) >= 20:
                    tap_moi_lay_duoc[chuoi_ngay_chuan] = ds_khong_trung
            except:
                continue
                
        return tap_moi_lay_duoc
    except Exception as e:
        print(f"Lỗi đồng bộ API JSON: {str(e)[:50]}")
        return {}

# --- Quy trình kiểm tra tuần tự và kích hoạt phân tích tự động ---
def lay_du_lieu_theo_thu_tu(ngay_batdau):
    bot.send_message(CHAT_ID, "🔄 Đang kết nối trực tiếp cổng dữ liệu API JSON chống chặn...")
    thong_bao_trang_thai = []
    
    for thu_tu, nguon in enumerate(DANH_SACH_NGUON_UU_TIEN, 1):
        thong_bao_trang_thai.append(f"🔹 {thu_tu}. Đang đồng bộ: {nguon['ten']}...")
        try:
            tap_moi = lay_tu_trang_tonghop(nguon["link"], ngay_batdau)
            if tap_moi:
                DA_CO_DU_LIEU.update(tap_moi)
                thong_bao_trang_thai.append(f"✅ Đồng bộ thành công! Đã quét và cập nhật dữ liệu tự động.")
            else:
                thong_bao_trang_thai.append(f"ℹ️ Máy chủ cổng {thu_tu} đang bận hoặc chưa nạp phiên mới...")
        except Exception as e:
            thong_bao_trang_thai.append(f"❌ Kết nối API trục trặc: {str(e)[:45]}...")
        time.sleep(1)

    # Đếm chính xác tổng số ngày hợp lệ hiện có trong bộ nhớ đệm
    tong_ngay_co = 0
    danh_sach_tat_ca_duoi = []
    for k in DA_CO_DU_LIEU:
        try:
            ng = datetime.strptime(k, "%d/%m/%Y")
            if 0 <= (ngay_batdau - ng).days < 60:
                tong_ngay_co += 1
                danh_sach_tat_ca_duoi.extend(DA_CO_DU_LIEU[k])
        except:
            pass

    thong_bao_trang_thai.append(f"\n📊 === TỔNG KẾT HIỆN CÓ: {tong_ngay_co}/45 ngày mức đủ tin cậy ===")
    
    if tong_ngay_co >= 45:
        bot.send_message(CHAT_ID, "\n".join(thong_bao_trang_thai) + "\n✅ Đủ chuẩn dữ liệu! Tiến hành phân tích thuật toán ngay...")
        
        # Gọi hàm tính toán điểm chuẩn dựa trên tổng hợp số đuôi thu thập được
        top3, top20 = tinh_diem_chuan(danh_sach_tat_ca_duoi)
        
        # Định dạng tin nhắn kết quả phân tích gửi trả người dùng
        chuoi_top3 = "\n".join([f"🔥 Top {i+1}: Số {ma} (Xuất hiện {sl} lần)" for i, (ma, sl) in enumerate(top3)])
        chuoi_top20 = ", ".join(top20)
        
        tin_nhan_kq = f"📊 **KẾT QUẢ PHÂN TÍCH THUẬT TOÁN 45 NGÀY** 📊\n\n🎯 **Top 3 số tiềm năng nhất:**\n{chuoi_top3}\n\n📋 **Danh sách Top 20 số chuẩn:**\n`{chuoi_top20}`"
        bot.send_message(CHAT_ID, tin_nhan_kq, parse_mode="Markdown")
        return True, DA_CO_DU_LIEU, "Đủ chuẩn"
    else:
        can_them = 45 - tong_ngay_co
        thong_bao_trang_thai.append(f"💡 Hệ thống tự động chưa gom đủ ngày (Thiếu {can_them} ngày).")
        thong_bao_trang_thai.append("📝 Bạn có thể gửi bổ sung thủ công bằng cú pháp sau để cộng dồn:\n`Luu du lieu: Ngày 19/08/2026 | Đuôi: 12,34,56...`")
        bot.send_message(CHAT_ID, "\n".join(thong_bao_trang_thai), parse_mode="Markdown")
        return False, {}, "Đang chờ bổ sung"

# --- Handler nhận lệnh nạp bổ sung số thủ công từ phía người dùng ---
@bot.message_handler(func=lambda msg: msg.text.strip().startswith("Luu du lieu:"))
def xu_ly_luu_ban_gui(msg):
    try:
        noi_dung = msg.text.strip().replace("Luu du lieu:", "").strip()
        phan_ngay = noi_dung.split("|")[0].replace("Ngày", "").strip()
        danh_sach_duoi = [d.strip() for d in noi_dung.split("|")[1].replace("Đuôi:", "").strip().split(",") if d.strip() and len(d.strip()) == 2]
        
        # Khôi phục và định dạng chuẩn ngày tháng (Sửa lỗi cú pháp dở dang từ code cũ)
        ngay_chuan = datetime.strptime(phan_ngay, "%d/%m/%Y").strftime("%d/%m/%Y")
        
        if len(danh_sach_duoi) >= 20:
            DA_CO_DU_LIEU[ngay_chuan] = list(dict.fromkeys(danh_sach_duoi))
            bot.reply_to(msg, f"📥 Đã nạp thành công dữ liệu ngày {ngay_chuan} vào bộ nhớ cộng dồn!")
            
            # Kích hoạt quét và tính toán lại ngay sau khi người dùng nạp số
            lay_du_lieu_theo_thu_tu(datetime.now())
        else:
            bot.reply_to(msg, "⚠️ Danh sách số đuôi không đúng chuẩn (Yêu cầu nhập đủ từ 20 cặp số loto trở lên, cách nhau bằng dấu phẩy).")
    except Exception as e:
        bot.reply_to(msg, f"❌ Lỗi xử lý định dạng chuỗi gửi lên: {str(e)}")

# --- Handler bắt lệnh kiểm tra trạng thái từ người dùng ---
@bot.message_handler(func=lambda msg: msg.text.strip().lower() == "trang thai")
def kiem_tra_trang_thai_tu_dong(msg):
    # Kích hoạt tiến trình đồng bộ API cho mốc ngày hiện tại
    lay_du_lieu_theo_thu_tu(datetime.now())

# Khởi chạy Polling nhận lệnh liên tục từ Telegram
if __name__ == "__main__":
    print("🚀 Bot XSMB API JSON đang chạy và sẵn sàng nhận lệnh từ Telegram...")
    bot.infinity_polling()
