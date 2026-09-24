import os
import re
import sys
import json
import threading
import traceback
from datetime import datetime, timedelta
from flask import Flask
import telebot
import requests
from bs4 import BeautifulSoup

# ==========================================
# 1. KHỞI TẠO WEB SERVER (RENDER KEEP-ALIVE)
# ==========================================
app = Flask(__name__)

@app.route('/')
def home():
    return "XSMB - XSMN - XSMT Multi-Region Engine V59: ONLINE", 200

@app.route('/health')
def health():
    return "OK", 200

# ==========================================
# 2. BOT CONFIGURATION & DATABASE MANAGER
# ==========================================
TOKEN = os.environ.get("BOT_TOKEN", "").strip()
DB_FILE = "lottery_db.json"

def load_database():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"mb": {}, "mn": {}, "mt": {}}

def save_database(db_data):
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(db_data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"⚠️ Lỗi lưu database: {e}", flush=True)

# ==========================================
# 3. HỆ THỐNG CÀO DỮ LIỆU THỰC TẾ & CHỐNG VƯỢT THỜI GIAN
# ==========================================
def fetch_lottery_result_live(region, date_str):
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    now = datetime.now()
    
    # CHẶN TUYỆT ĐỐI KHÔNG CÀO CÁC NGÀY TRONG TƯƠNG LAI
    if dt > now:
        return None

    d_str = dt.strftime("%d-%m-%Y")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'vi-VN,vi;q=0.9,en-US;q=0.8',
    }

    urls = []
    if region == 'mb':
        urls = [
            f"https://www.minhngoc.net.vn/ket-qua-xo-so/mien-bac/{d_str}.html",
            f"https://xosodaiphat.com/xs-mb-{d_str}.html"
        ]
    elif region == 'mn':
        urls = [
            f"https://www.minhngoc.net.vn/ket-qua-xo-so/mien-nam/{d_str}.html",
            f"https://xosodaiphat.com/xs-mn-{d_str}.html"
        ]
    elif region == 'mt':
        urls = [
            f"https://www.minhngoc.net.vn/ket-qua-xo-so/mien-trung/{d_str}.html",
            f"https://xosodaiphat.com/xs-mt-{d_str}.html"
        ]

    for url in urls:
        try:
            res = requests.get(url, headers=headers, timeout=8)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                cells = soup.find_all(['div', 'td', 'span'], class_=re.compile(r'(gdb|dacbiet|special)', re.I))
                for cell in cells:
                    text = cell.text.strip()
                    match = re.search(r'\d{5,6}', text)
                    if match:
                        val = match.group(0)
                        return val[-2:]
                
                for tr in soup.find_all('tr'):
                    row_text = tr.text.lower()
                    if 'đặc biệt' in row_text or 'g.đb' in row_text:
                        numbers = re.findall(r'\b\d{5,6}\b', tr.text)
                        if numbers:
                            return numbers[0][-2:]
        except Exception:
            continue

    return None

def get_db_result(region, date_str):
    """
    Lấy dữ liệu từ Database cache cục bộ (100 ngày gần nhất). 
    Nếu chưa có thì cào mới và lưu vào DB.
    """
    db = load_database()
    if region not in db:
        db[region] = {}

    # Nếu đã có trong kho dữ liệu, trả về luôn
    if date_str in db[region] and db[region][date_str] is not None:
        return db[region][date_str]

    # Nếu chưa có, tiến hành cào thực tế
    val = fetch_lottery_result_live(region, date_str)
    if val is not None:
        db[region][date_str] = val
        
        # Giới hạn database chỉ giữ tối đa 100 ngày gần nhất cho mỗi miền
        sorted_dates = sorted(db[region].keys())
        if len(sorted_dates) > 100:
            for old_date in sorted_dates[:-100]:
                del db[region][old_date]
                
        save_database(db)
        
    return val

# ==========================================
# 4. THUẬT TOÁN TỐI ƯU HIỆU SUẤT V59
# ==========================================
def generate_dan_so(size_target=40, region='mb'):
    all_numbers = [f"{i:02d}" for i in range(100)]
    scored_pool = []
    
    for num in all_numbers:
        d1, int_num = int(num[0]), int(num[1])
        d2 = int(num[1])
        score = 0
        total_sum = d1 + d2
        
        if total_sum in [3, 4, 7, 8, 11, 12, 15, 16]:
            score += 3.0
        if total_sum % 2 != 0:
            score += 2.0
            
        if region == 'mb':
            if d1 in [1, 2, 3, 7, 8] or d2 in [1, 3, 6, 8, 9]:
                score += 2.5
            if int_num % 4 == 0 or int_num % 7 == 0:
                score += 1.5
        elif region == 'mt':
            if d1 in [0, 1, 2, 5, 6, 8] or d2 in [0, 3, 5, 6, 9]:
                score += 3.0
            if total_sum in [5, 9, 13, 14]:
                score += 2.0
        else:
            if d1 in [1, 2, 4, 5, 8, 9] or d2 in [2, 3, 4, 7, 8]:
                score += 2.8
            if int_num % 3 == 0 or int_num % 5 == 0:
                score += 1.8

        scored_pool.append((score, -int_num, num))
        
    scored_pool.sort(key=lambda x: (x[0], x[1]), reverse=True)
    target_count = max(30, min(60, size_target))
    return sorted([item[2] for item in scored_pool[:target_count]])

def run_backtest_engine(region, start_date_str, total_days=10):
    try:
        start_dt = datetime.strptime(start_date_str, "%Y-%m-%d")
    except Exception:
        start_dt = datetime.now() - timedelta(days=10)
        
    total_days = max(1, min(40, total_days))
    region_name = "MIỀN BẮC" if region == 'mb' else ("MIỀN NAM" if region == 'mn' else "MIỀN TRUNG")
    
    header = f"🧪 BACKTEST {region_name} V59 (DB CACHE 100 NGÀY) - {total_days} KỲ TỪ: {start_date_str}\n\n"
    
    win_30, win_40, win_50 = 0, 0, 0
    valid_days_count = 0
    current_dt = start_dt
    today = datetime.now()
    
    details = []
    for i in range(total_days):
        # Không chạy vượt quá ngày hiện tại
        if current_dt > today:
            break
            
        date_str = current_dt.strftime("%Y-%m-%d")
        real_db = get_db_result(region, date_str)
        
        if real_db is not None:
            valid_days_count += 1
            dan_30 = generate_dan_so(30, region)
            dan_40 = generate_dan_so(40, region)
            dan_50 = generate_dan_so(50, region)
            
            hit_30 = real_db in dan_30
            hit_40 = real_db in dan_40
            hit_50 = real_db in dan_50
            
            if hit_30: win_30 += 1
            if hit_40: win_40 += 1
            if hit_50: win_50 += 1
            
            details.append(f"📅 {date_str} | ĐB Về: **{real_db}** (Thực tế)\n├ Dàn 30 số: {'✅ NỔ' if hit_30 else '❌ XỊT'}\n├ Dàn 40 số: {'✅ NỔ' if hit_40 else '❌ XỊT'}\n└ Dàn 50 số: {'✅ NỔ' if hit_50 else '❌ XỊT'}\n")
        else:
            details.append(f"📅 {date_str} | ⚠️ Chưa có kết quả hoặc dữ liệu chưa cập nhật\n")
        
        current_dt += timedelta(days=1)
        
    footer = f"\n📊 **THỐNG KÊ HIỆU SUẤT V59:**\n• Số kỳ lấy được dữ liệu: {valid_days_count}\n"
    if valid_days_count > 0:
        footer += f"• Dàn 30 số: {win_30}/{valid_days_count} ({round(win_30*100/valid_days_count, 1)}%)\n"
        footer += f"• Dàn 40 số: {win_40}/{valid_days_count} ({round(win_40*100/valid_days_count, 1)}%)\n"
        footer += f"• Dàn 50 số: {win_50}/{valid_days_count} ({round(win_50*100/valid_days_count, 1)}%)"
    else:
        footer += f"• Không có dữ liệu hợp lệ để tính toán hiệu suất."
        
    return header, details, footer

# ==========================================
# 5. HÀM GỬI TIN NHẮN AN TOÀN (CHỐNG TRÀN)
# ==========================================
def send_long_message(bot, message, header, details, footer):
    current_chunk = header
    for item in details:
        if len(current_chunk) + len(item) > 3800:
            bot.reply_to(message, current_chunk, parse_mode="Markdown")
            current_chunk = item
        else:
            current_chunk += "\n" + item
            
    current_chunk += "\n" + footer
    bot.reply_to(message, current_chunk, parse_mode="Markdown")

# ==========================================
# 6. KHỞI CHẠY BOT TELEGRAM (AN TOÀN)
# ==========================================
def run_telegram_bot():
    if not TOKEN:
        print("\n⚠️ CẢNH BÁO: CHƯA CẤU HÌNH 'BOT_TOKEN' TRÊN RENDER!\n", flush=True)
        return

    try:
        bot = telebot.TeleBot(TOKEN)

        @bot.message_handler(commands=['start', 'help'])
        def send_welcome(message):
            help_text = (
                "🤖 **XSMB - XSMN - XSMT MULTI-REGION BOT V59**\n\n"
                "📌 **Lệnh Dự Đoán:** `/dudoanmb`, `/dudoanmn`, `/dudoanmt`\n"
                "📌 **Lệnh Kiểm Thử:** `/testmb 2026-09-01=>15`, `/testmn`, `/testmt`\n"
                "📌 **Lệnh Hệ Thống:** `/reload`"
            )
            bot.reply_to(message, help_text, parse_mode="Markdown")

        @bot.message_handler(commands=['reload'])
        def handle_reload(message):
            reload_text = "🔄 **TẢI LẠI HỆ THỐNG V59 THÀNH CÔNG!**\n\n🌐 Đã kích hoạt cơ chế Database Cache 100 ngày & chặn ngày tương lai."
            bot.reply_to(message, reload_text, parse_mode="Markdown")

        @bot.message_handler(commands=['dudoanmb', 'dudoanmn', 'dudoanmt'])
        def handle_dudoan_regions(message):
            cmd = message.text.lower()
            region = 'mb'
            title = "MIỀN BẮC"
            if 'mn' in cmd:
                region = 'mn'
                title = "MIỀN NAM"
            elif 'mt' in cmd:
                region = 'mt'
                title = "MIỀN TRUNG"
                
            dan_30 = generate_dan_so(30, region)
            dan_40 = generate_dan_so(40, region)
            dan_50 = generate_dan_so(50, region)
            
            res_msg = (
                f"🎯 **DỰ ĐOÁN GIẢI ĐẶC BIỆT {title} HÔM NAY** (V59)\n\n"
                f"📌 **Dàn 30 số:**\n`{', '.join(dan_30)}`\n\n"
                f"📌 **Dàn 40 số:**\n`{', '.join(dan_40)}`\n\n"
                f"📌 **Dàn 50 số:**\n`{', '.join(dan_50)}`"
            )
            bot.reply_to(message, res_msg, parse_mode="Markdown")

        @bot.message_handler(commands=['testmb', 'testmn', 'testmt'])
        def handle_test_regions(message):
            try:
                cmd = message.text.strip().lower()
                region = 'mb'
                if 'testmn' in cmd:
                    region = 'mn'
                elif 'testmt' in cmd:
                    region = 'mt'
                    
                date_match = re.search(r'\d{4}-\d{2}-\d{2}', cmd)
                date_str = date_match.group(0) if date_match else "2026-09-01"
                
                days_match = re.search(r'=>\s*(\d+)', cmd)
                total_days = int(days_match.group(1)) if days_match else 10
            except Exception:
                region = 'mb'
                date_str = "2026-09-01"
                total_days = 10
                
            header, details, footer = run_backtest_engine(region, start_date_str=date_str, total_days=total_days)
            send_long_message(bot, message, header, details, footer)

        print("✅ Bot Telegram V59 đã khởi động thành công...", flush=True)
        bot.infinity_polling(timeout=60, long_polling_timeout=30)
    except Exception as e:
        print(f"💥 Lỗi khởi động Telegram Bot: {e}", flush=True)
        traceback.print_exc()

if __name__ == "__main__":
    print("🚀 Đang khởi động Web Server và Bot Engine V59...", flush=True)
    bot_thread = threading.Thread(target=run_telegram_bot)
    bot_thread.daemon = True
    bot_thread.start()

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)