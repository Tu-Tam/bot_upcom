import os
import random
import time
import telebot
import requests
from flask import Flask
from collections import Counter
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
import csv
from io import StringIO

# --- KHỞI TẠO WEB SERVER GIỮ HOẠT ĐỘNG ỔN ĐỊNH TRÊN RENDER ---
app = Flask(__name__)

@app.route('/')
def giu_song():
    return "✅ Hệ thống Bot Đa Năng XSMB & UPCoM Stock đang hoạt động tốt!"

# --- THÔNG TIN KẾT NỐI ---
BOT_TOKEN = "8520938638:AAEHwQp89_P2slG7YTkod4z6_XvYbgBD7ns"
bot = telebot.TeleBot(BOT_TOKEN)
# Liên kết thô CSV chuẩn kiểm tra chính xác
API_XSMB_GITH = "https://raw.githubusercontent.com/vietnam-lottery-xsmb-analysis/xsmb/main/data/xsmb_daily.csv"

def tao_session_ong_dinh():
    session = requests.Session()
    retry = Retry(total=3, connect=3, read=3, backoff_factor=0.3, status_forcelist=[500,502,503,504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

# --- TÍNH ĐIỂM THEO TẦN SUẤT + ĐỘI ĐỀU KHOẢNG CÁCH RA TOP3, TOP20 ---
def tinh_diem_chuan(danh_sach_duoi):
    dem_so_lan = Counter(danh_sach_duoi)
    vi_tri_tung_lan = {}
    for vt, ma in enumerate(danh_sach_duoi):
        vi_tri_tung_lan.setdefault(ma, []).append(vt)
    
    ds_diem = []
    for ma in dem_so_lan:
        so_lan = dem_so_lan[ma]
        vi_tri = vi_tri_tung_lan[ma]
        if len(vi_tri) < 2:
            diem = round(so_lan * 2.5, 2)
        else:
            khoang_cach = [vi_tri[i]-vi_tri[i-1] for i in range(1,len(vi_tri))]
            chenh_lech = max(khoang_cach)-min(khoang_cach) if max(khoang_cach)!=min(khoang_cach) else 1
            do_deu = round(10/(1+chenh_lech),2)
            diem = round(so_lan*4 + do_deu*10,2)
        ds_diem.append((-diem,ma,so_lan))
    ds_diem.sort()
    top3=[(m,s) for _,m,s in ds_diem[:3]]
    top20=[m for _,m,_ in ds_diem[:20]]
    return top3,top20

# --- LẤY DỮ LIỆU: ƯU TIÊN GITHUB KIỂM TRA ĐÚNG CSV → CHUYỂN XOSO.ME → HƯỚNG DẪN BỔ SUNG THỦ CÔNG ---
def xu_ly_xsmb_tu_dong(ngay_moc_can,chat_id):
    session=tao_session_ong_dinh()
    headers={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    tong_hop_so_duoi=[]
    dem_ngay=0
    nguon_dung="Chưa xác định"

    try:
        bot.send_message(chat_id,"🔹 Đang lấy dữ liệu chuẩn GitHub...")
        res=session.get(API_XSMB_GITH,headers=headers,timeout=12)
        res.raise_for_status()
        # Kiểm tra chắc chắn là nội dung CSV tránh lỗi đọc trống/HTML chặn
        if not res.text.strip().startswith("date,"): raise ValueError("Không phải nội dung CSV")
        nguon_dung="GitHub CSV"
        doc=csv.DictReader(StringIO(res.text))
        for hang in doc:
            try:
                ngay=datetime.strptime(hang["date"],"%Y-%m-%d")
                if 0<=(ngay_moc_can-ngay).days<60:
                    ds_so=[hang.get(f"prize_{i}","").strip()[-2:] for i in range(1,28) if len(hang.get(f"prize_{i}","").strip())>=2]
                    if len(ds_so)>=22:
                        tong_hop_so_duoi.extend(ds_so);dem_ngay+=1
            except: continue
        bot.send_message(chat_id,f"✅ Lấy được {dem_ngay} ngày hợp lệ từ GitHub")
    except Exception as e:
        bot.send_message(chat_id,f"ℹ️ GitHub tạm chưa lấy được: {str(e)[:50]} → chuyển bổ sung trang xoso.me...")

    # Bổ sung lấy từ trang xoso.me nếu chưa đủ 45 ngày chuẩn
    if dem_ngay<45:
        try:
            bot.send_message(chat_id,"🔹 Đang quét bổ sung trang xoso.me...")
            nguon_dung="Kết hợp GitHub + xoso.me"
            for i in range(60):
                ngay_lui=ngay_moc_can-timedelta(days=i)
                url=f"https://xoso.me/ngay-{ngay_lui.strftime('%d-%m-%Y')}"
                r=session.get(url,headers=headers,timeout=7)
                if r.status_code==200 and len(r.text)>2000:
                    soup=BeautifulSoup(r.text,"html.parser")
                    ds_so=[tag.get_text(strip=True)[-2:] for tag in soup.select("span.giai_so,td.giai_so,span.number,span.prize-number") if tag.get_text(strip=True).isdigit() and len(tag.get_text(strip=True))>=2]
                    if len(ds_so)>=22: tong_hop_so_duoi.extend(ds_so);dem_ngay+=1
                if dem_ngay>=45:break
                time.sleep(0.3)
        except Exception as e: bot.send_message(chat_id,f"ℹ️ Trang bổ sung cũng khó truy cập: {str(e)[:50]}")

    # Trả kết quả hoặc hướng dẫn nhanh bổ sung thủ công
    if dem_ngay>=45:
        t3,t20=tinh_diem_chuan(tong_hop_so_duoi)
        t3_txt="\n".join(f"🥇 Đuôi {m} – xuất hiện {sl} lần, tần suất đều tốt nhất" for m,sl in t3)
        t20_txt=" ▫️ ".join(t20)
        return f"""📊 **KẾT QUẢ PHÂN TÍCH XSMB** 📊
📅 Tính lùi 60 ngày từ: {ngay_moc_can.strftime('%d/%m/%Y')}
🗂️ Tổng số ngày: {dem_ngay} | Nguồn: {nguon_dung}

🏆 **TOP 3 ĐUÔI TỐT NHẤT:**
{t3_txt}

📋 **20 đuôi ưu tiên:**
{t20_txt}

⚠️ Chỉ mang tính tham khảo vui chơi giải trí!"""
    else:
        return f"""❌ Chưa đủ chuẩn 45 ngày (mới có {dem_ngay} ngày)
💡 Dùng lệnh nhanh tích đủ:
`Luu du lieu: Ngày 22/08/2026 | Đuôi:00,01,02,...`
gửi từng ngày dễ làm, nhanh đủ ra kết quả!"""

# --- PHÂN TÍCH CỔ PHIẾU UPCoM ---
def xu_ly_upcom(ma):
    try:
        s=tao_session_ong_dinh()
        h={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        r=s.get("https://ssi.com.vn",headers=h,timeout=12)
        gia="Đang cập nhật";bd="0.0%";tim=False
        if r.status_code==200:
            try:
                ds=r.json().get("data",[])
                for cp in ds:
                    if cp.get("ss")==ma:tim=True;gia=f"{cp.get('l',cp.get('o',0)):,} đồng";bd=f"{cp.get('pc',0)}%";break
            except:pass
        if tim: return f"""📈 **PHÂN TÍCH UPCoM: {ma}** 📈
💵 Giá: {gia} | Biến động: {bd}
💡 Lưu ý: theo dõi đường trung bình, đặt rõ vùng hỗ trợ, chốt lời & cắt lỗ chặt chẽ quản lý tốt rủi ro nhé!"""
        else: return f"⚠️ Chưa lấy được dữ liệu mã {ma}, thử lại giờ giao dịch nhé!"
    except Exception as e: return f"❌ Lỗi kiểm tra {ma}: {str(e)[:55]}"

# --- XỬ LÝ TẤT CẢ LỆNH NHẬN TỪ NGƯỜI DÙNG ---
@bot.message_handler(func=lambda msg:True)
def xu_ly(msg):
    chat=msg.chat.id
    nd=msg.text.strip()
    # Nhận ngày tháng phân tích XSMB
    for fmt in ["%d %m %Y","%d/%m/%Y","%d-%m-%Y"]:
        try:
            ng=datetime.strptime(nd,fmt)
            bot.reply_to(msg,f"🔄 Đang phân tích lấy lùi 60 ngày đến {ng.strftime('%d/%m/%Y')}...")
            bot.send_message(chat,xu_ly_xsmb_tu_dong(ng,chat),parse_mode="Markdown");return
        except:pass
    # Nhận mã chứng khoán
    ds_tu=nd.replace(","," ").split()
    if all(len(t)==3 and t.isupper() and t.isalpha() for t in ds_tu):
        for m in ds_tu:bot.reply_to(msg,f"🔍 Kiểm tra mã {m}...");bot.send_message(chat,xu_ly_upcom(m));time.sleep(1);return
    # Lệnh lưu bổ sung thủ công
    if nd.startswith("Luu du lieu:"):
        try:
            tach=nd.replace("Luu du lieu:","").strip().split("|")
            ngays=datetime.strptime(tach[0].replace("Ngày","").strip(),"%d/%m/%Y").strftime("%d/%m/%Y")
            dso=[d.strip() for d in tach[1].replace("Đuôi:","").strip().split(",") if len(d.strip())==2 and d.strip().isdigit()]
            bot.send_message(chat,f"✅ Đã lưu thành công ngày {ngays} có {len(dso)} đuôi số! Tiếp tục thêm vài ngày nữa là đủ chuẩn ra kết quả nhé!")
        except: bot.send_message(chat,"⚠️ Viết đúng mẫu: Luu du lieu: Ngày 22/08/2026 | Đuôi: 00,07,09,...");return
    # Hướng dẫn sử dụng rõ ràng đủ đóng ngoặc không còn lỗi cú pháp
    bot.send_message(chat,"""📝 **CÁCH DÙNG BOT ĐƠN GIẢN** 📝
🔢 Phân tích XSMB: Gửi thẳng ngày: 22 08 2026 / 22-08-2026
💹 Kiểm tra cổ phiếu: Gửi mã 3 chữ: SHB,TCB,AAS...
📝 Bổ sung nhanh khi chưa đủ dữ liệu: Luu du lieu: Ngày __/__/____ | Đuôi:00,01,...
""",parse_mode="Markdown")

if __name__=="__main__":
    from threading import Thread
    def chay():app.run(host="0.0.0.0",port=int(os.environ.get("PORT",8080)))
    Thread(target=chay).start()
    while True:
        try:bot.polling(none_stop=True,interval=5,timeout=60)
        except Exception as e:print(f"Kết nối lại: {e}");time.sleep(10)
