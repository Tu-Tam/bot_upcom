import os
import random
from flask import Flask
from threading import Thread
import time
import telebot
import requests
from collections import Counter
from datetime import datetime

# --- Khởi tạo Web Server giữ song song ---
app = Flask(__name__)
@app.route('/')
def giu_song():
    return "✅ Bot XSMB API đang chạy ngầm ổn định!"

def chay_server():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

Thread(target=chay_server).start()

# --- Cấu hình Tài khoản Bot ---
BOT_TOKEN = "8520938638:AAEHwQp89_P2slG7YTkod4z6_XvYbgBD7ns"
CHAT_ID = 7064473358
bot = telebot.TeleBot(BOT_TOKEN)

DA_CO_DU_LIEU = {}

DANH_SACH_NGUON_UU_TIEN = [
    {
        "ten": "Kho dữ liệu mở XSMB toàn diện (GitHub API)", 
        "link": "https://githubusercontent.com"
    }
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

def lay_tu_trang_tonghop(link, ngay_moc_can):
    tap_moi_lay_duoc = {}
    try:
        res = requests.get(link, timeout=15)
        if res.status_code != 200: return {}
        data = res.json()
        
        for ngay_str, giai_list in data.items():
            try:
                dt_lay = datetime.strptime(ngay_str, "%Y-%m-%d")
                chuoi_ngay_chuan = dt_lay.strftime("%d/%m/%Y")
                
                # Mở rộng biên độ kiểm tra ngày để tránh lệch múi giờ máy chủ đám mây
                so_ngay_ke = (ngay_moc_can - dt_lay).days
                if not (-2 <= so_ngay_ke < 90): 
                    continue
                
                ds_so = [giai[-2:] for giai in giai_list if len(giai) >= 2]
                ds_khong_trung = list(dict.fromkeys(ds_so))
                
                if len(ds_khong_trung) >= 20:
                    tap_moi_lay_duoc[chuoi_ngay_chuan] = ds_khong_trung
            except:
                continue
                
        return tap_moi_lay_duoc
    except Exception as e:
        print(f"Lỗi tải dữ liệu JSON: {str(e)}")
        return {}

def lay_du_lieu_theo_thu_tu(ngay_batdau):
    try:
        bot.send_message(CHAT_ID, "🔄 Đang kết nối trực tiếp cổng dữ liệu API JSON chống chặn...")
    except Exception as e:
        print(f"Không thể gửi tin nhắn Telegram, kiểm tra Token/ChatID: {e}")
        return False, {}, "Lỗi kết nối Telegram"

    thong_bao_trang_thai = []
    for thu_tu, nguon in enumerate(DANH_SACH_NGUON_UU_TIEN, 1):
        thong_bao_trang_thai.append(f"🔹 {thu_tu}. Đang đồng bộ: {nguon['ten']}...")
        try:
            tap_moi = lay_tu_trang_tonghop(nguon["link"], ngay_batdau)
            if tap_moi:
                DA_CO_DU_LIEU.update(tap_moi)
                thong_bao_trang_thai.append(f"✅ Đồng bộ thành công! Đã tự động cập nhật dữ liệu lịch sử.")
            else:
                thong_bao_trang_thai.append(f"ℹ️ Không tìm thấy ngày mới phù hợp từ cổng {thu_tu}...")
        except Exception as e:
            thong_bao_trang_thai.append(f"❌ Kết nối API trục trặc: {str(e)[:45]}...")

    tong_ngay_co = 0
    danh_sach_tat_ca_duoi = []
    for k in DA_CO_DU_LIEU:
        try:
            ng = datetime.strptime(k, "%d/%m/%Y")
            if -2 <= (ngay_batdau - ng).days < 90:
                tong_ngay_co += 1
                danh_sach_tat_ca_duoi.extend(DA_CO_DU_LIEU[k])
        except:
            pass

    thong_bao_trang_thai.append(f"\n📊 === TỔNG KẾT HIỆN CÓ: {tong_ngay_co}/45 ngày mức đủ tin cậy ===")
    
    if tong_ngay_co >= 45:
        bot.send_message(CHAT_ID, "\n".join(thong_bao_trang_thai) + "\n✅ Đủ chuẩn dữ liệu! Tiến hành phân tích ngay...")
        top3, top20 = tinh_diem_chuan(danh_sach_tat_ca_duoi)
        
        chuoi_top3 = "\n".join([f"🔥 Top {i+1}: Số {ma} (Xuất hiện {sl} lần)" for i, (ma, sl) in enumerate(top3)])
        chuoi_top20 = ", ".join(top20)
        
        tin_nhan_kq = f"📊 **KẾT QUẢ PHÂN TÍCH THUẬT TOÁN 45 NGÀY** 📊\n\n🎯 **Top 3 số tiềm năng nhất:**\n{chuoi_top3}\n\n📋 **Danh sách Top 20 số chuẩn:**\n`{chuoi_top20}`"
        bot.send_message(CHAT_ID, tin_nhan_kq, parse_mode="Markdown")
        return True, DA_CO_DU_LIEU, "Đủ chuẩn"
    else:
        can_them = 45 - tong_ngay_co
        thong_bao_trang_thai.append(f"💡 Hệ thống tự động chưa gom đủ ngày (Thiếu {can_them} ngày).")
        thong_bao_trang_thai.append("📝 Gửi bổ sung thủ công bằng cú pháp:\n`Luu du lieu: Ngày 19/08/2026 | Đuôi: 12,34,56...`")
        bot.send_message(CHAT_ID, "\n".join(thong_bao_trang_thai), parse_mode="Markdown")
        return False, {}, "Đang chờ bổ sung"

@bot.message_handler(func=lambda msg: msg.text.strip().startswith("Luu du lieu:"))
def xu_ly_luu_ban_gui(msg):
    try:
        noi_dung = msg.text.strip().replace("Luu du lieu:", "").strip()
        
        # SỬA LỖI TÁCH CHUỖI CŨ TẠI ĐÂY:
        phan_giao_tuan = noi_dung.split("|")
        phan_ngay = phan_giao_tuan[0].replace("Ngày", "").strip()
        danh_sach_duoi = [d.strip() for d in phan_giao_tuan[1].replace("Đuôi:", "").strip().split(",") if d.strip() and len(d.strip()) == 2]
        
        ngay_chuan = datetime.strptime(phan_ngay, "%d/%m/%Y").strftime("%d/%m/%Y")
        
        if len(danh_sach_duoi) >= 20:
            DA_CO_DU_LIEU[ngay_chuan] = list(dict.fromkeys(danh_sach_duoi))
            bot.reply_to(msg, f"📥 Đã nạp thành công dữ liệu ngày {ngay_chuan} vào bộ nhớ cộng dồn!")
            lay_du_lieu_theo_thu_tu(datetime.now())
        else:
            bot.reply_to(msg, "⚠️ Danh sách số đuôi không đúng chuẩn (Yêu cầu nhập từ 20 cặp số loto trở lên).")
    except Exception as e:
        bot.reply_to(msg, f"❌ Lỗi xử lý định dạng chuỗi gửi lên: {str(e)}")

@bot.message_handler(func=lambda msg: msg.text.strip().lower() == "trang thai")
def kiem_tra_trang_thai_tu_dong(msg):
    lay_du_lieu_theo_thu_tu(datetime.now())

if __name__ == "__main__":
    print("🚀 Bot XSMB API JSON đang khởi chạy...")
    bot.infinity_polling()
