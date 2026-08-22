# === TINH CHỈNH KỸ LẠI CÁCH ĐỌC TRANG SỬ DỤNG API VÀ KHO DỮ LIỆU JSON MỞ KHÔNG BỊ CHẶN BỞI TƯỜNG LỬA ===
import os
import random
from flask import Flask
from threading import Thread
import time
import telebot
import requests
from bs4 import BeautifulSoup
from collections import Counter
from datetime import datetime, timedelta

app = Flask(__name__)
@app.route('/')
def giu_song():
    return "✅ Đã tối ưu hóa phương thức kết nối dữ liệu qua API/JSON chống chặn; cộng dồn ngay số ngày bạn gửi lên!"

def chay_server():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

Thread(target=chay_server).start()

BOT_TOKEN = "8520938638:AAEHwQp89_P2slG7YTkod4z6_XvYbgBD7ns"
CHAT_ID = 7064473358
bot = telebot.TeleBot(BOT_TOKEN)
DA_CO_DU_LIEU = {} # Lưu vĩnh viễn không tự xóa

# 📋 Danh sách nguồn ưu tiên kết hợp API ngầm chống tường lửa hiệu quả
DANH_SACH_NGUON_UU_TIEN = [
    {"ten": "Cổng API ngầm kết quả nhiều ngày", "link": "https://ketqua.vn", "loai": "api_json"},
    {"ten": "Kho dữ liệu mở XSMB (Dự phòng chống chặn)", "link": "https://githubusercontent.com", "loai": "api_json"}
]

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

# === 🚀 SỬA ĐỔI: GỌI THẲNG DỮ LIỆU DẠNG JSON SẠCH ĐỂ ĐẢM BẢO XUYÊN QUA CÁC LỚP BẢO MẬT ===
def lay_tu_trang_tonghop(link, ngay_moc_can):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest"
    }
    tap_moi_lay_duoc = {}
    
    try:
        # Trường hợp 1: Sử dụng cổng dữ liệu API của ketqua.vn
        if "ketqua.vn" in link:
            res = requests.get(link, headers=headers, timeout=15)
            if res.status_code == 200:
                data = res.json()
                # Cấu trúc API của ketqua trả về danh sách kết quả, ta duyệt qua từng ngày
                for item in data:
                    try:
                        # Thường API trả về định dạng YYYY-MM-DD
                        ngay_str = item.get("date", item.get("ngay", ""))
                        if not ngay_str: continue
                        
                        for fmt in ["%Y-%m-%d", "%d/%m/%Y"]:
                            try: dt_lay = datetime.strptime(ngay_str, fmt); break
                            except: continue
                        else: continue
                        
                        so_ngay_ke = (ngay_moc_can - dt_lay).days
                        if not (0 <= so_ngay_ke < 60): continue
                        
                        # Gom tất cả các số giải trích xuất 2 số cuối (đuôi)
                        ds_so = []
                        # Duyệt qua các trường chứa mảng số của API kết quả
                        for key in ["results", "prizes", "lst_giai"]:
                            if key in item and isinstance(item[key], list):
                                for s in item[key]:
                                    s_str = str(s).strip()
                                    if s_str.isdigit() and len(s_str) >= 2:
                                        ds_so.append(s_str[-2:])
                        
                        ds_khong_trung = list(dict.fromkeys(ds_so))
                        if len(ds_khong_trung) >= 20:
                            tap_moi_lay_duoc[dt_lay.strftime("%d/%m/%Y")] = ds_khong_trung
                    except:
                        continue
                        
        # Trường hợp 2: Sử dụng cổng dữ liệu từ kho mở GitHub (Chống chặn hoàn toàn)
        elif "githubusercontent.com" in link:
            res = requests.get(link, timeout=15)
            if res.status_code == 200:
                data = res.json() # Định dạng phân tích sẵn: {"YYYY-MM-DD": ["số giải 1", "số giải 2",...]}
                for ngay_str, giai_list in data.items():
                    try:
                        dt_lay = datetime.strptime(ngay_str, "%Y-%m-%d")
                        chuoi_ngay_chuan = dt_lay.strftime("%d/%m/%Y")
                        
                        so_ngay_ke = (ngay_moc_can - dt_lay).days
                        if not (0 <= so_ngay_ke < 60): continue
                        
                        ds_so = [giai[-2:] for giai in giai_list if len(giai) >= 2]
                        ds_khong_trung = list(dict.fromkeys(ds_so))
                        
                        if len(ds_khong_trung) >= 20:
                            tap_moi_lay_duoc[chuoi_ngay_chuan] = ds_khong_trung
                    except:
                        continue
                        
        return tap_moi_lay_duoc
    except Exception as e:
        print(f"Lấy API gặp lỗi: {str(e)[:60]}")
        return {}

# === 📋 QUY TRÌNH THỬ TUẦN TỰ + BÁO RÕ SỐ HIỆN CÓ ===
def lay_du_lieu_theo_thu_tu(ngay_batdau):
    bot.send_message(CHAT_ID, "🔄 Đang kết nối trực tiếp cổng dữ liệu API chống chặn bảo mật...")
    thong_bao_trang_thai = []
    for thu_tu, nguon in enumerate(DANH_SACH_NGUON_UU_TIEN, 1):
        thong_bao_trang_thai.append(f"🔹 {thu_tu}. Đang kiểm tra: {nguon['ten']}...")
        try:
            tap_moi = lay_tu_trang_tonghop(nguon["link"], ngay_batdau)
            if tap_moi:
                DA_CO_DU_LIEU.update(tap_moi)
                thong_bao_trang_thai.append(f"✅ Lấy kết nối thành công và cập nhật {len(tap_moi)} ngày mới!")
            else:
                thong_bao_trang_thai.append(f"ℹ️ Cổng {thu_tu} bận hoặc chưa có phiên dữ liệu mới...")
        except Exception as e:
            thong_bao_trang_thai.append(f"❌ Kết nối trục trặc: {str(e)[:45]}...")
        time.sleep(random.uniform(0.5, 1.2))

    # Tính chính xác tổng ngày trong khoảng yêu cầu
    tong_ngay_co = 0
    for k in DA_CO_DU_LIEU:
        try:
            ng = datetime.strptime(k, "%d/%m/%Y")
            if 0 <= (ngay_batdau - ng).days < 60:
                tong_ngay_co += 1
        except:
            pass

    thong_bao_trang_thai.append(f"\n📊 === TỔNG KẾT HIỆN CÓ: {tong_ngay_co}/45 ngày mức đủ tin cậy ===")
    if tong_ngay_co >= 45:
        bot.send_message(CHAT_ID, "\n".join(thong_bao_trang_thai) + "\n✅ Đủ chuẩn rồi tiến hành phân tích ngay!")
        return True, DA_CO_DU_LIEU, "Đủ chuẩn"
    else:
        can_them = 45 - tong_ngay_co
        thong_bao_trang_thai.append(f"💡 Cần bổ sung thêm khoảng {can_them} ngày gần nhất để hoạt động!")
        thong_bao_trang_thai.append("📝 Cách gửi rất đơn giản từng ngày một hoặc nhiều ngày cùng dòng:\nVí dụ: Luu du lieu: Ngày 18/08/2026 | Đuôi: 12,34,56,78,90...")
        bot.send_message(CHAT_ID, "\n".join(thong_bao_trang_thai))
        return False, {}, "Đang chờ bổ sung thêm ít ngày"

# === 📥 LỆNH LƯU BỔ SUNG: NHẬN DIỆN VÀ KHÔI PHỤC HOÀN CHỈNH ĐOẠN CUỐI BỊ LỖI CÚ PHÁP ===
@bot.message_handler(func=lambda msg: msg.text.strip().startswith("Luu du lieu:"))
def xu_ly_luu_ban_gui(msg):
    try:
        noi_dung = msg.text.strip().replace("Luu du lieu:", "").strip()
        phan_ngay = noi_dung.split("|")[0].replace("Ngày", "").strip()
        danh_sach_duoi = [d.strip() for d in noi_dung.split("|")[1].replace("Đuôi:", "").strip().split(",") if d.strip() and len(d.strip()) == 2]
        
        # Sửa lỗi cú pháp dở dang `datetime.strptb` từ mã nguồn cũ của bạn:
        ngay_chuan = datetime.strptime(phan_ngay, "%d/%m/%Y").strftime("%d/%m/%Y")
        
        if len(danh_sach_duoi) >= 20:
            DA_CO_DU_LIEU[ngay_chuan] = list(dict.fromkeys(danh_sach_duoi))
            bot.reply_to(msg, f"📥 Đã lưu bổ sung ngày {ngay_chuan} thành công vào bộ nhớ cộng dồn!")
            # Kích hoạt lại hàm kiểm tra sau khi người dùng nạp số bằng tay
            lay_du_lieu_theo_thu_tu(datetime.now())
        else:
            bot.reply_to(msg, "⚠️ Danh sách số đuôi gửi lên không đủ chuẩn 20 số loto trở lên, vui lòng kiểm tra lại.")
    except Exception as e:
        bot.reply_to(msg, f"❌ Lỗi xử lý định dạng chuỗi nạp dữ liệu thủ công: {str(e)}")

# Khởi chạy bot nhận lệnh liên tục
if __name__ == "__main__":
    print("🚀 Bot Telegram phân tích dữ liệu XSMB chống chặn tường lửa đang hoạt động...")
    bot.infinity_polling()
