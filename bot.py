import os
import re
import sys
import random
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
    return "XSMB - XSMN - XSMT Multi-Region Engine V51: ONLINE", 200

@app.route('/health')
def health():
    return "OK", 200

# ==========================================
# 2. BOT CONFIGURATION
# ==========================================
TOKEN = os.environ.get("BOT_TOKEN", "").strip()

# ==========================================
# 3. HỆ THỐNG CÀO DỮ LIỆU TRỰC TIẾP TỪ WEB
# ==========================================
def fetch_lottery_result(region, date_str):
    """Cào kết quả trực tiếp từ các trang web xổ số theo ngày và miền"""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    d_str = dt.strftime("%d-%m-%Y")
    d_slash = dt.strftime("%d/%m/%Y")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept-Language': 'vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7'
    }

    urls = []
    if region == 'mb':
        urls = [
            f"https://www.minhngoc.net.vn/ket-qua-xo-so/mien-bac/{d_str}.html",
            f"https://xosodaiphat.com/xs-mb-{d_str}.html",
            f"https://www.minhngoc.com.vn/ket-qua-xo-so/mien-bac/{d_str}.html"
        ]
    elif region == 'mn':
        urls = [
            f"https://www.minhngoc.net.vn/ket-qua-xo-so/mien-nam/{d_str}.html",
            f"https://xosodaiphat.com/xs-mn-{d_str}.html",
            f"https://www.minhngoc.com.vn/ket-qua-xo-so/mien-nam/{d_str}.html"
        ]
    elif region == 'mt':
        urls = [
            f"https://www.minhngoc.net.vn/ket-qua-xo-so/mien-trung/{d_str}.html",
            f"https://xosodaiphat.com/xs-mt-{d_str}.html",
            f"https://www.minhngoc.com.vn/ket-qua-xo-so/mien-trung/{d_str}.html"
        ]

    for url in urls:
        try:
            res = requests.get(url, headers=headers, timeout=6)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                
                # Tìm kiếm theo các định dạng bảng kết quả phổ biến
                special_cell = (
                    soup.find('div', {'id': 'gdb'}) or 
                    soup.find('td', {'class': 'gdb'}) or 
                    soup.find('div', {'class': 'special-prize'}) or
                    soup.find('span', {'class': 'special-prize'})
                )
                
                if special_cell:
                    match = re.search(r'\d{5,6}', special_cell.text.strip())
                    if match:
                        return match.group(0)[-2:]
                
                # Quét toàn bộ văn bản trong bảng kết quả đặc biệt
                for tag in soup.find_all(['div', 'span', 'td', 'b']):
                    text = tag.text.strip()
                    if text.isdigit() and len(text) in [5, 6]:
                        parent_text = tag.parent.text.lower()
                        if 'đặc biệt' in parent_text or 'db' in parent_text or 'Giải ĐB' in tag.parent.text:
                            return text[-2:]
        except Exception:
            continue

    return None  # Trả về None nếu không cào được để kiểm tra lỗi kết nối

def get_available_data_stats():
    return {'mb': 100, 'mn': 100, 'mt': 100}

# ==========================================
# 4. THUẬT TOÁN SINH DÀN SỐ V51
# ==========================================
def generate_dan_so(size_target=50):
    all_numbers = [f"{i:02d}" for i in range(100)]
    scored_pool = []
    for num in all_numbers:
        d1, d2 = int(num[0]), int(num[1])
        score = 0
        total_sum = d1 + d2
        if total_sum % 2 != 0:
            score += 3
        if total_sum in [3, 5, 7, 9, 11, 13, 15]:
            score += 4
        if d1 in [0, 2, 5, 7] or d2 in [0, 2, 5, 7]:
            score += 2
        scored_pool.append((score, -int(num), num))
        
    scored_pool.sort(key=lambda x: (x[0], x[1]), reverse=True)
    target_count = max(30, min(60, size_target))
    return sorted([item[2] for item in scored_pool[:target_count]])

def run_backtest_engine(region, start_date_str, total_days=10):
    try:
        start_dt = datetime.strptime(start_date_str, "%Y-%m-%d")
    except Exception:
        start_dt = datetime.now() - timedelta(days=10)
        
    total_days = max(1, min(100, total_days))
    region_name = "MIỀN BẮC" if region == 'mb' else ("MIỀN NAM" if region == 'mn' else "MIỀN TRUNG")
    
    output = f"🧪 BACKTEST {region_name} V51 (CÀO WEB TRỰC TIẾP) - {total_days} KỲ TỪ: {start_date_str}\n\n"
    
    win_30, win_40, win_50 = 0, 0, 0
    current_dt = start_dt
    
    success_fetches = 0
    for i in range(total_days):
        date_str = current_dt.strftime("%Y-%m-%d")
        real_db = fetch_lottery_result(region, date_str)
        
        if real_db:
            success_fetches += 1
        else:
            real_db = "??(Lỗi Web)"

        dan_30 = generate_dan_so(30)
        dan_40 = generate_dan_so(40)
        dan_50 = generate_dan_so(50)
        
        hit_30 = (real_db != "??(Lỗi Web)" and real_db in dan_30)
        hit_40 = (real_db != "??(Lỗi Web)" and real_db in dan_40)
        hit_50 = (real_db != "??(Lỗi Web)" and real_db in dan_50)
        
        if hit_30: win_30 += 1
        if hit_40: win_40 += 1
        if hit_50: win_50 += 1
        
        if total_days <= 15:
            output += f"📅 {date_str} | ĐB Về: **{real_db}**\n"
            if real_db != "??(Lỗi Web)":
                output += f"├ Dàn 30 số: {'✅ NỔ' if hit_30 else '❌ XỊT'}\n"
                output += f"├ Dàn 40 số: {'✅ NỔ' if hit_40 else '❌ XỊT'}\n"
                output += f"└ Dàn 50 số: {'✅ NỔ' if hit_50 else '❌ XỊT'}\n\n"
            else:
                output += f"└ ⚠️ Không kết nối được dữ liệu web ngày này.\n\n"
        
        current_dt += timedelta(days=1)
        
    output += f"📊 **THỐNG KÊ HIỆU SUẤT ({total_days} KỲ):**\n"
    output += f"• Tỷ lệ kết nối web thành công: {success_fetches}/{total_days}\n"
    output += f"• Dàn 30 số: {win_30}/{total_days} ({round(win_30*100/total_days, 1)}%)\n"
    output += f"• Dàn 40 số: {win_40}/{total_days} ({round(win_40*100/total_days, 1)}%)\n"
    output += f"• Dàn 50 số: {win_50}/{total_days} ({round(win_50*100/total_days, 1)}%)"
    return output

# ==========================================
# 5. KHỞI CHẠY BOT TELEGRAM
# ==========================================
def run_telegram_bot():
    if not TOKEN:
        print("\n⚠️ CHƯA CẤU HÌNH 'BOT_TOKEN' TRÊN RENDER!\n", flush=True)
        return

    try:
        bot = telebot.TeleBot(TOKEN)

        @bot.message_handler(commands=['start', 'help'])
        def send_welcome(message):
            help_text = (
                "🤖 **XSMB - XSMN - XSMT MULTI-REGION BOT V51**\n\n"
                "📌 **Lệnh Dự Đoán:** `/dudoanmb`, `/dudoanmn`, `/dudoanmt`\n"
                "📌 **Lệnh Kiểm Thử (Cào web trực tiếp):** `/testmb 2026-08-01=>10`, `/testmn`, `/testmt`\n"
                "📌 **Lệnh Hệ Thống:** `/reload`"
            )
            bot.reply_to(message, help_text, parse_mode="Markdown")

        @bot.message_handler(commands=['reload'])
        def handle_reload(message):
            reload_text = "🔄 **TẢI LẠI HỆ THỐNG V51 THÀNH CÔNG!**\n\n🌐 Đã chuyển sang chế độ cào dữ liệu trực tiếp từ web."
            bot.reply_to(message, reload_text, parse_mode="Markdown")

        @bot.message_handler(commands=['dudoanmb', 'dudoanmn', 'dudoanmt'])
        def handle_dudoan_regions(message):
            cmd = message.text.lower()
            title = "MIỀN BẮC"
            if 'mn' in cmd:
                title = "MIỀN NAM"
            elif 'mt' in cmd:
                title = "MIỀN TRUNG"
                
            dan_30 = generate_dan_so(30)
            dan_40 = generate_dan_so(40)
            dan_50 = generate_dan_so(50)
            
            res_msg = (
                f"🎯 **DỰ ĐOÁN GIẢI ĐẶC BIỆT {title} HÔM NAY** (V51)\n\n"
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
                date_str = date_match.group(0) if date_match else "2026-08-01"
                
                days_match = re.search(r'=>\s*(\d+)', cmd)
                total_days = int(days_match.group(1)) if days_match else 10
            except Exception:
                region = 'mb'
                date_str = "2026-08-01"
                total_days = 10
                
            result_text = run_backtest_engine(region, start_date_str=date_str, total_days=total_days)
            bot.reply_to(message, result_text, parse_mode="Markdown")

        print("✅ Bot Telegram V51 đã chạy thành công...", flush=True)
        bot.infinity_polling(timeout=60, long_polling_timeout=30)
    except Exception as e:
        print(f"💥 Lỗi Telegram Bot: {e}", flush=True)
        traceback.print_exc()

if __name__ == "__main__":
    print("🚀 Đang khởi động hệ thống Multi-Region Engine V51...", flush=True)
    bot_thread = threading.Thread(target=run_telegram_bot)
    bot_thread.daemon = True
    bot_thread.start()

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)