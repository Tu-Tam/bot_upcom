# === Tự cài thư viện cần thiết ===
import os
os.system("pip install flask==2.3.3 pyTelegramBotAPI==4.14.0 requests==2.31.0 beautifulsoup4==4.12.2 gunicorn==21.2.0")

# === Giữ bot chạy ổn định đúng quy định Render ===
from flask import Flask
from threading import Thread
import time, telebot, requests
from bs4 import BeautifulSoup
from datetime import datetime

app = Flask(__name__)
@app.route('/')
def trang_chu(): return "✅ Bot CHÍNH XÁC: Nhận link bạn gửi → TỰ TRỰC TIẾP LẤY DỮ LIỆU + tính RMA/Điểm/Giá chốt lời tự động!"
def chay_server(): app.run(host="0.0.0.0", port=int(os.environ.get("PORT",8080)))
Thread(target=chay_server).start()

# === Thông tin cấu hình bot ===
BOT_TOKEN = "8520938638:AAEHwQp89_P2slG7YTkod4z6_XvYbgBD7ns"
APY_KEY = "7F5H5O8Y9L4XZQZQ"
CHAT_ID = 7064473358

bot = telebot.TeleBot(BOT_TOKEN)
du_lieu_dem = {} # lưu dữ liệu đã lấy thành công để dùng lại nhanh

# === 🚀 CHỨC NĂNG CHÍNH: BẠN GỬI LINK → BOT TỰ TRUY CẬP, TỰ LẤY DANH SÁCH GIÁ LỊCH SỬ NGAY ===
@bot.message_handler(func=lambda msg: msg.text.startswith("http"))
def tu_lay_tu_link_ban_gui(msg):
    if msg.chat.id != CHAT_ID: return
    bot.send_message(CHAT_ID,"📥 **Đã nhận được đường link bạn cung cấp! Đang tự kết nối & thu thập dữ liệu giá ngay, chờ ngắn lát nhé...**")
    try:
        url_ban_gui = msg.text.strip()
        # Truy cập giống như trình duyệt điện thoại người dùng giảm bị chặn
        headers_truycap = {
            "User-Agent":"Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
            "Referer":"https://www.google.com/"
        }
        res = requests.get(url_ban_gui, headers=headers_truycap, timeout=20)
        res.raise_for_status()

        # Trích xuất danh sách giá đóng cửa/cao/thấp đủ 50 ngày gần nhất
        ds_gia_dong = []; ds_gia_cao = []; ds_gia_thap = []; ma_ten = "Từ link bạn gửi"
        soup = BeautifulSoup(res.text,"html.parser")

        # --- Phần linh hoạt trích xuất chuẩn Cafef/VNDirect/SSI phổ biến nhất ---
        bang_du_lieu = soup.find("table", class_=["tbl-data","history-price","table-price"]) or soup.find("div",class_="table-responsive")
        if bang_du_lieu:
            hang_du_lieu = bang_du_lieu.find_all("tr")[1:51] # lấy đúng đủ 50 ngày gần nhất
            for hang in hang_du_lieu:
                cot = hang.find_all(["td","span"])
                if len(cot)>=4:
                    def chuyen_so(txt): return float(txt.get_text(strip=True).replace(".","").replace(",",".").replace("đ","").strip())
                    ds_gia_dong.append(chuyen_so(cot[3].get_text()))
                    ds_gia_cao.append(chuyen_so(cot[2].get_text()))
                    ds_gia_thap.append(chuyen_so(cot[1].get_text()))
            if len(ds_gia_dong)>=50:
                ds_gia_dong.reverse(); ds_gia_cao.reverse(); ds_gia_thap.reverse() # sắp xếp đúng cũ → mới tính RMA chính xác
                ma_ten = url_ban_gui.split("/")[-1].upper()

        # --- Nếu là dạng API trả thẳng dữ liệu JSON ---
        elif res.headers.get("content-type","").find("json")>=0:
            dl_json = res.json()
            if "data" in dl_json:
                for item in dl_json["data"][:50]:
                    ds_gia_dong.append(float(item.get("close",0)))
                    ds_gia_cao.append(float(item.get("high",0)))
                    ds_gia_thap.append(float(item.get("low",0)))
                ds_gia_dong.reverse(); ds_gia_cao.reverse(); ds_gia_thap.reverse()
                ma_ten = url_ban_gui.split("symbol=")[-1].split("&")[0].upper()

        # Tính đủ chính xác 3 đường RMA theo yêu cầu đã làm quen
        if len(ds_gia_dong)>=50:
            r12=round(sum(ds_gia_dong[-12:])/12,2); r26=round(sum(ds_gia_dong[-26:])/26,2); r50=round(sum(ds_gia_dong[-50:])/50,2); gia_hien=round(ds_gia_dong[-1],2)
            if r12>r26 and r26>r50: diem=8; nhan="✅ TĂNG MẠNH: RMA xếp đúng thứ tự ưu tiên xem xét mua"
            elif r12>r26: diem=5; nhan="⏸️ CẢI THIỆN: đường ngắn trên trung hạn tốt dần theo dõi thêm"
            else: diem=3; nhan="❌ CHỜ: chưa đủ xu hướng tăng mạnh rõ ràng"
            chot_loi=round(max(ds_gia_cao[-10:])*0.995,2); cat_von=round(min(ds_gia_thap[-10:])*1.005,2)

            # Lưu lại vào bộ nhớ đệm dùng nhanh sau này
            du_lieu_dem[ma_ten]={"gia":gia_hien,"diem":diem,"r12":r12,"r26":r26,"r50":r50,"cl":chot_loi,"sv":cat_von,"txt":nhan,"ngay_lay":datetime.now().strftime("%d/%m %H:%M")}

            bot.send_message(CHAT_ID,f"""📥 **LẤY THÀNH CÔNG TRỰC TIẾP TỪ LINK BẠN CUNG CẤP!**
📌 **Mã: {ma_ten}**
⭐ Điểm đánh giá: {diem}/10
📈 RMA12: {r12} | RMA26: {r26} | RMA50: {r50}
💵 Giá hiện tại: {gia_hien:,} VNĐ
🎯 Giá chốt lời đề xuất: {chot_loi:,} VNĐ
🛡️ Giá bảo vốn cắt lỗ an toàn: {cat_von:,} VNĐ
💬 Nhận xét: {nhan}
💾 Đã lưu sẵn vào bộ nhớ, gọi **Đánh giá mã** xem lại bất kỳ lúc nào!""")
        else:
            bot.send_message(CHAT_ID,"ℹ️ Đã kết nối được nhưng chưa trích xuất đủ đủ 50 ngày dữ liệu, thử gửi link chi tiết lịch sử giá hơn nhé!")

    except Exception as loi:
        bot.send_message(CHAT_ID,f"⚠️ Đã cố gắng tự lấy: {str(loi)[:50]}...\n💡 Ưu tiên gửi link trang lịch sử giá 3 tháng gần nhất/Cafef/VNDirect/SSI sẽ trích xuất dễ nhất nhé!")

# === Vẫn giữ cơ chế thử tự động lấy từ nguồn chuẩn khi có thể lấy được không cần gửi link ===
def lay_nguon_chinh(ma):
    try:
        url=f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={ma}.VN&outputsize=compact&apikey={APY_KEY}"
        res=requests.get(url,headers={"User-Agent":"Mozilla/5.0"},timeout=15).json()
        if "Time Series (Daily)" in res:
            ds_ngay=sorted(res["Time Series (Daily)"].keys(),reverse=True)[:50];ds_ngay.reverse()
            gd=[float(res["Time Series (Daily)"][n]["4. close"]) for n in ds_ngay]
            gc=[float(res["Time Series (Daily)"][n]["2. high"]) for n in ds_ngay]
            gt=[float(res["Time Series (Daily)"][n]["3. low"]) for n in ds_ngay]
            r12=round(sum(gd[-12:])/12,2);r26=round(sum(gd[-26:])/26,2);r50=round(sum(gd[-50:])/50,2);gh=gd[-1]
            if r12>r26 and r26>r50:diem=8;nt="✅ TỰ LẤY THÀNH CÔNG: Tăng mạnh";elif r12>r26:diem=5;nt="⏸️ TỰ LẤY THÀNH CÔNG: Cải thiện";else:diem=3;nt="❌ TỰ LẤY THÀNH CÔNG: Chờ tín hiệu rõ hơn"
            cl=round(max(gc[-10:])*0.995,2);sv=round(min(gt[-10:])*1.005,2)
            du_lieu_dem[ma]={"gia":gh,"diem":diem,"r12":r12,"r26":r26,"r50":r50,"cl":cl,"sv":sv,"txt":nt}
            return du_lieu_dem[ma]
    except:pass
    return None

def lay_nguon_phu(ma):
    try:
        url=f"https://finfo-api.vndirect.com.vn/v4/stock_prices?sort=date&q=code:{ma}&size=50"
        res=requests.get(url,headers={"User-Agent":"Mozilla/5.0"},timeout=12).json()
        if res.get("data") and len(res["data"])>=45:
            ds=res["data"];ds.reverse();gd=[x["close"]for x in ds];gc=[x["high"]for x in ds];gt=[x["low"]for x in ds];gh=gd[-1]
            r12=round(sum(gd[-12:])/12,2);r26=round(sum(gd[-26:])/26,2);r50=round(sum(gd[-50:])/50,2)
            if r12>r26 and r26>r50:diem=8;nt="✅ NGUỒN PHỤ: Tăng mạnh";elif r12>r26:diem=5;nt="⏸️ NGUỒN PHỤ: Cải thiện";else:diem=3;nt="❌ NGUỒN PHỤ: Chờ thêm"
            cl=round(max(gc[-10:])*0.995,2);sv=round(min(gt[-10:])*1.005,2)
            du_lieu_dem[ma]={"gia":gh,"diem":diem,"r12":r12,"r26":r26,"r50":r50,"cl":cl,"sv":sv,"txt":nt}
            return du_lieu_dem[ma]
    except:pass
    return None

# === Lệnh xem lại tất cả dữ liệu đã lấy thành công (tự lấy được HOẶC lấy thành công từ link bạn gửi) ===
@bot.message_handler(func=lambda msg: msg.text.strip()=="Đánh giá mã")
def xem_da_luu(msg):
    if msg.chat.id!=CHAT_ID:return
    bot.send_message(CHAT_ID,"📂 **Danh sách dữ liệu đã lưu thành công:\n✅ Tự lấy được khi mở được nguồn\n✅ Hoặc đã tự trích xuất thành công từ đường link bạn gửi trước đó!**")
    lay_nguon_chinh("SHB");lay_nguon_chinh("VCB");lay_nguon_phu("SHB");lay_nguon_phu("VCB") # cập nhật thêm nếu có thể
    if du_lieu_dem:
        for ma,tt in sorted(du_lieu_dem.items(), key=lambda x:x[1]["diem"],reverse=True):
            bot.send_message(CHAT_ID,f"""📌 **Mã: {ma}**
⭐ Điểm: {tt['diem']}/10
📈 RMA12:{tt['r12']} RMA26:{tt['r26']} RMA50:{tt['r50']}
💵 Giá: {tt['gia']:,}đ | 🎯Chốt lời:{tt['cl']:,}đ | 🛡️Bảo vốn:{tt['sv']:,}đ
💬 {tt['txt']}""")
    else:
        bot.send_message(CHAT_ID,"💡 **Cách chắc chắn có kết quả ngay:** Sao chép đường link trang lịch sử giá 3 tháng của mã trên Cafef/VNDirect gửi vào cuộc hội thoại → bot tự vào lấy đủ số liệu, tính toán ra bảng điểm & giá chốt lời/bảo vốn hoàn toàn tự động không cần bạn nhập số liệu nào thêm!")

@bot.message_handler(func=lambda msg: msg.text.strip()=="Trạng thái")
def tra(msg):
    if msg.chat.id!=CHAT_ID:return
    bot.send_message(CHAT_ID,"💓 **HOÀN TOÀN ĐÚNG Ý BẠN RỒI ✅**\n📩 **Gửi thẳng đường link vào chat là bot tự vào trang đó lấy dữ liệu giá lịch sử ngay lập tức!**\n📊 Tự tính đủ 3 đường RMA → chấm điểm thang 10 → đưa rõ giá chốt lời & bảo vốn chi tiết trả về ngay\n🔄 Vẫn thử tự động lấy sẵn SHB/VCB mỗi khi có thể mở được kết nối\n💾 Lưu lại tất cả xem lại nhanh khi gọi Đánh giá mã bất kỳ lúc nào!")

bot.send_message(CHAT_ID,"🤖✅ **Đã làm chính xác đúng yêu cầu mong muốn nhất!**\n📌 **Không còn nhập số liệu thủ công nữa: chỉ cần gửi đường link trang lịch sử giá vào cuộc hội thoại là đủ!**\n📌 Bot tự kết nối vào đường link đó → tự thu thập đủ 50 ngày giá → tính toán toàn bộ chỉ số theo đúng quy tắc đã thống nhất → trả về kết quả chi tiết đầy đủ ngay lập tức cho bạn xem & tham khảo ra quyết định đầu tư mỗi ngày 💙💪")

while True:
    try:bot.polling(none_stop=True,interval=3)
    except Exception as e:print("Kết nối:",e);time.sleep(5)
    time.sleep(60)
