import os
import re
import sys
import json
import threading
import traceback
from datetime import datetime, timedelta, time
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
    return "XSMB - XSMN - XSMT Multi-Region Engine V63: ONLINE", 200

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
# 3. HỆ THỐNG KIỂM TRA GIỜ QUAY & CHẶN NGÀY CHƯA QUAY
# ==========================================
def is_date_already_drawn(date_str, region):
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        now = datetime.now()
        today = now.date()
        
        if target_date > today:
            return False
        if target_date == today:
            current_time = now.time()
            if region == 'mn' and current_time < time(16, 35):
                return False
            if region == 'mt' and current_time < time(17, 40):
                return False
            if region == 'mb' and current_time < time(18, 45):
                return False
    except Exception:
        pass
    return True

def fetch_full_lottery_data(region, date_str):
    """
    Cào toàn bộ bảng kết quả (ĐB và toàn bộ các giải lô) để thu thập 
    tất cả các cặp số xuất hiện trong ngày làm dữ liệu phân tích.
    """
    if not is_date_already_drawn(date_str, region):
        return None, None

    dt = datetime.strptime(date_str, "%Y-%m-%d")
    d_str = dt.strftime("%d-%m-%Y")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }

    urls = []
    if region == 'mb':
        urls = [f"https://www.minhngoc.net.vn/ket-qua-xo-so/mien-bac/{d_str}.html"]
    elif region == 'mn':
        urls = [f"https://www.minhngoc.net.vn/ket-qua-xo-so/mien-nam/{d_str}.html"]
    elif region == 'mt':
        urls = [f"https://www.minhngoc.net.vn/ket-qua-xo-so/mien-trung/{d_str}.html"]

    for url in urls:
        try:
            res = requests.get(url, headers=headers, timeout=6)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                
                # 1. Lấy riêng giải đặc biệt để chấm điểm kết quả (ĐB về)
                special_val = None
                cells = soup.find_all(['div', 'td', 'span'], class_=re.compile(r'(gdb|dacbiet|special)', re.I))
                for cell in cells:
                    match = re.search(r'\d{5,6}', cell.text.strip())
                    if match:
                        special_val = match.group(0)[-2:]
                        break
                if not special_val:
                    for tr in soup.find_all('tr'):
                        if 'đặc biệt' in tr.text.lower() or 'g.đb' in tr.text.lower():
                            numbers = re.findall(r'\b\d{5,6}\b', tr.text)
                            if numbers:
                                special_val = numbers[0][-2:]
                                break

                # 2. Lấy toàn bộ các số xuất hiện trong bảng (Lô từ G7 đến GĐB)
                all_numbers_in_board = []
                for span in soup.find_all(['div', 'td', 'span', 'p']):
                    text_val = span.text.strip()
                    # Tìm tất cả các chuỗi số từ 2 đến 6 chữ số
                    found_nums = re.findall(r'\b\d{2,6}\b', text_val)
                    for fn in found_nums:
                        # Lấy 2 số cuối của mỗi giải làm lô tô
                        all_numbers_in_board.append(fn[-2:])
                
                if special_val and len(all_numbers_in_board) > 5:
                    return special_val, all_numbers_in_board
        except Exception:
            continue
    return None, None

def get_db_result(region, date_str):
    db = load_database()
    if region not in db:
        db[region] = {"special": {}, "all_lotes": {}}

    # Tương thích cấu trúc cũ và mới
    if "special" not in db[region]:
        db[region] = {"special": db[region], "all_lotes": {}}

    if date_str in db[region]["special"] and db[region]["special"][date_str] is not None:
        return db[region]["special"][date_str], db[region]["all_lotes"].get(date_str, [])

    special_val, all_lotes = fetch_full_lottery_data(region, date_str)
    if special_val is not None:
        db[region]["special"][date_str] = special_val
        db[region]["all_lotes"][date_str] = all_lotes
        
        # Giới hạn cache 100 ngày
        sorted_dates = sorted(db[region]["special"].keys())
        if len(sorted_dates) > 100:
            for old_date in sorted_dates[:-100]:
                db[region]["special"].pop(old_date, None)
                db[region]["all_lotes"].pop(old_date, None)
        save_database(db)
        
    return special_val, all_lotes

# ==========================================
# 4. THUẬT TOÁN TÍNH ĐIỂM DỰA TRÊN TOÀN BỘ LÔ TÔ (V63)
# ==========================================
def generate_dan_so_v63(size_target=40, region='mb', history_lotes=None):
    """
    Thuật toán V63 quét toàn bộ tần suất xuất hiện của các chạm/đầu/đuôi 
    từ tất cả các giải lô của các kỳ gần nhất để tối ưu tỷ lệ trúng.
    """
    all_numbers = [f"{i:02d}" for i in range(100)]
    score_map = {num: 5.0 for num in all_numbers}
    
    if history_lotes and len(history_lotes) > 0:
        # Gộp toàn bộ lô tô từ các kỳ gần nhất (tối đa 5 kỳ gần đây)
        recent_lotes = []
        for lotes_list in history_lotes[-5:]:
            recent_lotes.extend(lotes_list)
            
        digit_freq = {str(i): 0 for i in range(10)}
        tail_freq = {str(i): 0 for i in range(10)}
        exact_lote_freq = {}
        
        for lt in recent_lotes:
            if len(lt) == 2:
                d, t = lt[0], lt[1]
                digit_freq[d] += 1
                tail_freq[t] += 1
                exact_lote_freq[lt] = exact_lote_freq.get(lt, 0) + 1
                
        # Chấm điểm dựa trên tần suất lô tô thực tế xuất hiện trong bảng kết quả
        for num in all_numbers:
            d, t = num[0], num[1]
            # Thưởng điểm cao nếu cặp số hoặc chạm/đầu/đuôi xuất hiện nhiều trong bảng lô
            score_map[num] += (digit_freq.get(d, 0) * 1.8) + (tail_freq.get(t, 0) * 1.8)
            if num in exact_lote_freq:
                score_map[num] += exact_lote_freq[num] * 2.5
                
            # Cân đối tổng chạm theo vùng miền
            tong = (int(d) + int(t)) % 10
            if region == 'mb':
                if tong in [1, 3, 5, 7, 9]:
                    score_map[num] += 3.0
            else:
                if tong in [0, 2, 4, 6, 8]:
                    score_map[num] += 3.0

    scored_pool = [(score_map[num], -int(num), num) for num in all_numbers]
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
    
    header = f"🧪 BACKTEST {region_name} V63 (PHÂN TÍCH TOÀN BỘ LÔ TÔ) - {total_days} KỲ TỪ: {start_date_str}\n\n"
    
    win_30, win_40, win_50 = 0, 0, 0
    valid_days_count = 0
    current_dt = start_dt
    
    history_lotes_buffer = []
    details = []
    
    for i in range(total_days):
        date_str = current_dt.strftime("%Y-%m-%d")
        
        if not is_date_already_drawn(date_str, region):
            break
            
        real_db, all_lotes = get_db_result(region, date_str)
        
        if real_db is not None:
            valid_days_count += 1
            
            dan_30 = generate_dan_so_v63(30, region, history_lotes_buffer)
            dan_40 = generate_dan_so_v63(40, region, history_lotes_buffer)
            dan_50 = generate_dan_so_v63(50, region, history_lotes_buffer)
            
            hit_30 = real_db in dan_30
            hit_40 = real_db in dan_40
            hit_50 = real_db in dan_50
            
            if hit_30: win_30 += 1
            if hit_40: win_40 += 1
            if hit_50: win_50 += 1
            
            if all_lotes:
                history_lotes_buffer.append(all_lotes)
            
            details.append(f"📅 {date_str} | ĐB Về: **{real_db}** (Thực tế)\n├ Dàn 30 số: {'✅ NỔ' if hit_30 else '❌ XỊT'}\n├ Dàn 40 số: {'✅ NỔ' if hit_40 else '❌ XỊT'}\n└ Dàn 50 số: {'✅ NỔ' if hit_50 else '❌ XỊT'}\n")
        else:
            break
        
        current_dt += timedelta(days=1)
        
    footer = f"\n📊 **THỐNG KÊ HIỆU SUẤT V63:**\n• Số kỳ lấy được dữ liệu chuẩn: {valid_days_count}\n"
    if valid_days_count > 0:
        footer += f"• Dàn 30 số: {win_30}/{valid_days_count} ({round(win_30*100/valid_days_count, 1)}%)\n"
        footer += f"• Dàn 40 số: {win_40}/{valid_days_count} ({round(win_40*100/valid_days_count, 1)}%)\n"
        footer += f"• Dàn 50 số: {win_50}/{valid_days_count} ({round(win_50*100/valid_days_count, 1)}%)"
    else:
        footer += f"• Không có dữ liệu hợp lệ (hoặc chưa đến giờ quay hôm nay)."
        
    return header, details, footer

# ==========================================
# 5. HÀM GỬI TIN NHẮN AN TOÀN
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
# 6. KHỞI CHẠY BOT TELEGRAM
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
                "🤖 **XSMB - XSMN - XSMT MULTI-REGION BOT V63**\n\n"
                "📌 **Lệnh Dự Đoán:** `/dudoanmb`, `/dudoanmn`, `/dudoanmt`\n"
                "📌 **Lệnh Kiểm Thử:** `/testmb 2026-09-01=>15`, `/testmn`, `/testmt`\n"
                "📌 **Lệnh Hệ Thống:** `/reload`"
            )
            bot.reply_to(message, help_text, parse_mode="Markdown")

        @bot.message_handler(commands=['reload'])
        def handle_reload(message):
            reload_text = "🔄 **TẢI LẠI HỆ THỐNG V63 THÀNH CÔNG!**\n\n🚀 Đã kích hoạt cơ chế phân tích toàn bộ bảng lô tô từ G7 đến GĐB."
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
                
            dan_30 = generate_dan_so_v63(30, region)
            dan_40 = generate_dan_so_v63(40, region)
            dan_50 = generate_dan_so_v63(50, region)
            
            res_msg = (
                f"🎯 **DỰ ĐOÁN GIẢI ĐẶC BIỆT {title} HÔM NAY** (V63)\n\n"
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

        print("✅ Bot Telegram V63 đã khởi động thành công...", flush=True)
        bot.infinity_polling(timeout=60, long_polling_timeout=30)
    except Exception as e:
        print(f"💥 Lỗi khởi động Telegram Bot: {e}", flush=True)
        traceback.print_exc()

if __name__ == "__main__":
    print("🚀 Đang khởi động Web Server và Bot Engine V63...", flush=True)
    bot_thread = threading.Thread(target=run_telegram_bot)
    bot_thread.daemon = True
    bot_thread.start()

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)