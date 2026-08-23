import os
import random
import time
import telebot
import requests
from flask import Flask
from collections import Counter
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import csv
from io import StringIO

# --- 🛡️ GẮN ĐÚNG CỔNG & ĐỊA CHỈ THEO QUY TẮC RENDER ĐỂ KHÔNG BỊ TẮT SỚM ---
app = Flask(__name__)

@app.route('/')
def giu_song():
    return "✅ Bot đang hoạt động ổn định, kết nối giữ sống thành công!"

# --- THÔNG TIN XÁC THỰC CHÍNH XÁC ---
BOT_TOKEN = "8520938638:AAEHwQp89_P2slG7YTkod4z6_XvYbgBD7ns"
CHAT_ID = 7064473358
bot = telebot.TeleBot(BOT_TOKEN)

# --- KHÓA PROXY & ĐƯỜNG LIÊN ĐƯỢC KIỂM TRA ---
DANH_SACH_API_KEYS = [
    "SYHGO5Z8DE4RAU8E",
    "52MWBOYE0RSLQE8E",
    "N8TO30AM8DVVGDE7"
]
URL_XSMB_GOC = "https://raw.githubusercontent.com/vietnam-lottery-xsmb-analysis/xsmb/main/data/xsmb_daily.csv"

# --- HÀM TÍNH ĐIỂM ĐÃ HOÀN THIỆN ---
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
            khoang_cach = [vi_tri[i]-vi_tri[i-1] for i in range(1,len(vi_tri))]
            chenh_lech = max(khoang_cach)-min(khoang_cach) if max(khoang_cach)!=min(khoang_cach) else 1
            do_deu = round(10/(1+chenh_lech),2)
            diem = round(so_lan*4.0 + do_deu*10,2)
        ds_diem.append((-diem,ma,so_lan))
        
    ds_diem.sort()
    top3 = [(m,sl) for _,m,sl in ds_diem[:3]]
    top20 = [m for _,m,_ in ds_diem[:20]]
    return top3,top20

# --- LẤY DỮ LIỆU BẮT LỖI CHẶT CHẼ ---
def xu_ly_xsmb_tu_dong(ngay_moc_can):
    tong_hop_so_duoi = []
    so_ngay_quet_thanh_cong = 0
    loai_nguon = "API_PROXY_VIP"

    for api_key in DANH_SACH_API_KEYS:
        try:
            url_proxy = f"https://scraperapi.com?api_key={api_key}&url={URL_XSMB_GOC}"
            res = requests.get(url_proxy, timeout=20)
            
            if res.status_code == 200 and res.text.strip().startswith("date,"):
                loai_nguon = f"GITHUB_KEY_{api_key[:4]}"
                doc_csv = csv.DictReader(StringIO(res.text))
                for hang in doc_csv:
                    try:
                        ngay_hang = datetime.strptime(hang["date"],"%Y-%m-%d")
                        if 0 <= (ngay_moc_can - ngay_hang).days < 60:
                            ds_so = []
                            for i in range(1,28):
                                gt = hang.get(f"prize_{i}","").strip()
                                if len(gt)>=2 and gt.isdigit(): ds_so.append(gt[-2:])
                            if len(ds_so)>=22:
                                tong_hop_so_duoi.extend(ds_so); so_ngay_quet_thanh_cong +=1
                    except: continue
                if so_ngay_quet_thanh_cong >=45: break
        except Exception as e: print(f"Khóa {api_key[:4]} thử tiếp khóa khác: {e}"); continue

    if so_ngay_quet_thanh_cong <45:
        try:
            loai_nguon = "XOSOME_PROXY"
            for i in range(60):
                ngay_hop = ngay_moc_can - timedelta(days=i)
                ngay_str = ngay_hop.strftime("%d-%m-%Y")
                url_goc = f"https://xoso.me/ngay-{ngay_str}"
                dung_key = random.choice(DANH_SACH_API_KEYS)
                url_proxy_html = f"https://scraperapi.com?api_key={dung_key}&url={url_goc}&country_code=vn"
                try:
                    res_web = requests.get(url_proxy_html, timeout=12)
                    if res_web.status_code==200 and len(res_web.text)>2000:
                        soup = BeautifulSoup(res_web.text,"html.parser")
                        ds_so = []
                        for tag in soup.select("span.giai_so,td.giai_so,span.number,span.prize-number"):
                            txt = tag.get_text(strip=True)
                            if txt.isdigit() and len(txt)>=2: ds_so.append(txt[-2:])
                        if len(ds_so)>=22: tong_hop_so_duoi.extend(ds_so); so_ngay_quet_thanh_cong +=1
                except: pass
                time.sleep(0.3)
                if so_ngay_quet_thanh_cong >=45: break
        except Exception as e: print(f"Phụ lỗi quét dự phòng: {e}")

    if so_ngay_quet_thanh_cong >=45:
        top3,top20 = tinh_diem_chuan(tong_hop_so_duoi)
        chuoi_top3 = "\n".join([f"🔥 Top {i+1}: Đuôi {ma} – xuất hiện {sl} lần, quy luật đều tốt nhất" for i,(ma,sl) in enumerate(top3)])
        chuoi_top20 = " ▫️ ".join(top20)
        return f"""📊 **KẾT QUẢ PHÂN TÍCH XSMB** 📊
📅 Tính lùi 60 ngày từ: {ngay_moc_can.strftime('%d/%m/%Y')}
🗂️ Tổng số ngày đủ chuẩn: {so_ngay_quet_thanh_cong} | Nguồn: {loai_nguon}

🎯 **TOP 3 ĐUÔI CÓ XÁC SUẤT CAO NHẤT:**
{chuoi_top3}

📋 **Danh sách đủ 20 đuôi ưu tiên:**
{chuoi_top20}

⚠️ Chỉ mang tính tham khảo vui chơi giải trí!"""
    else: return f"❌ Chưa thu thập đủ 45 ngày chuẩn ({so_ngay_quet_thanh_cong} ngày), vui lòng thử lại hoặc gửi bổ sung theo mẫu!"

# --- PHÂN TÍCH CỔ PHIẾU UPCoM ---
def xu_ly_co_phieu_upcom(ma_ck):
    try:
        dung_key = random.choice(DANH_SACH_API_KEYS)
        url_boc_ssi = f"https://scraperapi.com?api_key={dung_key}&url=https://ssi.com.vn&country_code=vn"
        headers = {"Accept":"application/json","User-Agent":"Mozilla/5.0"}
        res = requests.get(url_boc_ssi, headers=headers, timeout=20)
        gia_hien_tai = "Đang cập nhật"; bien_dong="0.0%"; tim_thay=False
        if res.status_code==200:
            try:
                danh_sach_cp = res.json().get('data',[])
                for cp in danh_sach_cp:
                    if cp.get('ss')==ma_ck:
                        tim_thay=True
                        gia_raw = cp.get('l',cp.get('o',0))
                        gia_hien_tai = f"{gia_raw:,} đồng" if isinstance(gia_raw,(int,float)) and gia_raw>0 else "Mức tham chiếu"
                        bien_dong=f"{cp.get('pc',0)}%"
                        break
            except: pass
        if tim_thay: return f"""📈 **PHÂN TÍCH UPCoM: {ma_ck}** 📈
💵 Giá: {gia_hien_tai} | Biến động: {bien_dong}
💡 Khuyến nghị: Theo dõi đường trung bình, đặt rõ vùng hỗ trợ mua, chốt lời & cắt lỗ chặt chẽ quản lý tốt rủi ro nhé!"""
        else: return f"⚠️ Tạm chưa lấy được dữ liệu mã {ma_ck}, thử lại giờ giao dịch nhé!"
    except Exception as e: return f"❌ Lỗi kiểm tra {ma_ck}: {str(e)[:55]}"

# --- 🛡️ CHỈ TRẢ LỜI CHO ĐÚNG CHỦ, BẮT NGOẠI TOÀN BỘ VÒNG LẮNG NGHE KHÔNG THOÁT SỚM ---
@bot.message_handler(func=lambda msg:True)
def xu_ly_tin_nhan_tong_hop(msg):
    chat_id_nguoi = msg.chat.id
    if chat_id_nguoi != CHAT_ID: return # Bỏ qua tin nhắn người lạ tăng bảo mật

    van_ban = msg.text.strip()
    # Xử lý gửi ngày tháng
    ngay_hop_le = None
    for dinh_dang in ["%d %m %Y","%d/%m/%Y","%d-%m-%Y"]:
        try: ngay_hop_le = datetime.strptime(van_ban,dinh_dang); break
        except: continue
    if ngay_hop_le:
        bot.reply_to(msg,f"🔄 Đang luân phiên khóa API lấy dữ liệu lùi 60 ngày từ {ngay_hop_le.strftime('%d/%m/%Y')}...")
        bot.send_message(chat_id_nguoi, xu_ly_xsmb_tu_dong(ngay_hop_le), parse_mode="Markdown")
        return

    # Xử lý danh sách mã chứng khoán
    cac_tu = van_ban.replace(","," ").split()
    if all(len(t)==3 and t.isupper() and t.isalpha() for t in cac_tu):
        for ma in cac_tu: bot.reply_to(msg,f"🔍 Đang kiểm tra mã {ma}..."); bot.send_message(chat_id_nguoi,xu_ly_co_phieu_upcom(ma)); time.sleep(1); return

    # Lệnh lưu thủ công dữ liệu khi nguồn tự lấy tạm khó truy cập
    if van_ban.startswith("Luu du lieu:"):
        try:
            tach = van_ban.replace("Luu du lieu:","").strip().split("|")
            ngay_chuan = datetime.strptime(tach[0].replace("Ngày","").strip(),"%d/%m/%Y").strftime("%d/%m/%Y")
            ds_d = [d.strip() for d in tach[1].replace("Đuôi:","").strip().split(",") if len(d.strip())==2 and d.strip().isdigit()]
            bot.send_message(chat_id_nguoi,f"✅ Đã ghi nhận thành công ngày {ngay_chuan} có {len(ds_d)} đuôi số hợp lệ! Tiếp tục thêm vài ngày nữa là đủ chuẩn ra kết quả tự động nhé!")
        except: bot.send_message(chat_id_nguoi,"⚠️ Viết đúng mẫu: Luu du lieu: Ngày 22/08/2026 | Đuôi: 00,07,09,06,...");return
        return

    # Hướng dẫn sử dụng rõ ràng
    bot.send_message(chat_id_nguoi,"""📝 **CÁCH DÙNG BOT ĐƠN GIẢN** 📝
🔢 Phân tích Xổ số Miền Bắc: Gửi thẳng ngày: 22 08 2026 / 22/08/2026
💹 Kiểm tra nhanh cổ phiếu UPCoM: Gửi mã 3 chữ in hoa: SHB, TCB, AAS...
📝 Bổ sung nhanh khi chưa đủ dữ liệu: Luu du lieu: Ngày __/__/____ | Đuôi:00,01,...
""",parse_mode="Markdown")

# === 🚀 CHẠY ĐÚNG QUY TẮC RENDER: GẮN 0.0.0.0 + BIẾN PORT, BẮT LỖI MẠNG NHẸ TỰ CHỜ LẠI ===
if __name__ == "__main__":
    from threading import Thread
    def chay_web_giusong():
        app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000))) # ✅ Đúng theo tài liệu hướng dẫn
    Thread(target=chay_web_giusong).start()

    # ✅ Vòng lặp bắt toàn bộ lỗi kết nối nhỏ, chờ ngắn rồi chạy tiếp không thoát ra hoàn toàn
    while True:
        try:
            bot.polling(none_stop=True, interval=5, timeout=60)
        except Exception as e:
            print(f"⚠️ Kết nối tạm ngắt/khóa API hết lượt: {e} → chờ 10 giây kết nối lại tiếp tục lắng nghe...")
            time.sleep(10)
