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
    return "XSMB - XSMN - XSMT Multi-Region Engine V67: ONLINE", 200

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
# 3. HỆ THỐNG KIỂM TRA GIỜ QUAY & CÀO DỮ LIỆU
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

                all_numbers_in_board = []
                for span in soup.find_all(['div', 'td', 'span', 'p']):
                    text_val = span.text.strip()
                    found_nums = re.findall(r'\b\d{2,6}\b', text_val)
                    for fn in found_nums:
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

    if "special" not in db[region]:
        db[region] = {"special": db[region], "all_lotes": {}}

    if date_str in db[region]["special"] and db[region]["special"][date_str] is not None:
        return db[region]["special"][date_str], db[region]["all_lotes"].get(date_str, [])

    special_val, all_lotes = fetch_full_lottery_data(region, date_str)
    if special_val is not None:
        db[region]["special"][date_str] = special_val
        db[region]["all_lotes"][date_str] = all_lotes
        
        sorted_dates = sorted(db[region]["special"].keys())
        if len(sorted_dates) > 150:
            for old_date in sorted_dates[:-150]:
                db[region]["special"].pop(old_date, None)
                db[region]["all_lotes"].pop(old_date, None)
        save_database(db)
        
    return special_val, all_lotes

# ==========================================
# 4. THUẬT TOÁN V67 (5 ĐẦU, 5 ĐUÔI & CHẴN/LẺ)
# ==========================================
def analyze_heads_tails_parity(region='mb', history_lotes=None):
    """
    Phân tích và tính toán:
    1. Top 5 Đầu đề tỷ lệ cao nhất
    2. Top 5 Đuôi đề tỷ lệ cao nhất
    3. Dự đoán Chẵn hoặc Lẻ (cả Đầu, Đuôi và Tổng)
    """
    digit_score = {str(i): 1.0 for i in range(10)}
    tail_score = {str(i): 1.0 for i in range(10)}
    
    chan_count = 0
    le_count = 0
    
    if history_lotes and len(history_lotes) > 0:
        recent_windows = history_lotes[-10:] # Quét 10 kỳ gần nhất
        for idx, lotes in enumerate(recent_windows):
            weight = 1.0 + (idx * 0.25)
            for lt in lotes:
                if len(lt) == 2:
                    d, t = lt[0], lt[1]
                    digit_score[d] += weight
                    tail_score[t] += weight
                    
                    # Thống kê chẵn lẻ từ dữ liệu thực tế
                    if int(lt) % 2 == 0:
                        chan_count += 1
                    else:
                        le_count += 1

    # Sắp xếp lấy Top 5 Đầu & Top 5 Đuôi
    sorted_heads = sorted(digit_score.keys(), key=lambda x: digit_score[x], reverse=True)[:5]
    sorted_tails = sorted(tail_score.keys(), key=lambda x: tail_score[x], reverse=True)[:5]
    
    sorted_heads.sort()
    sorted_tails.sort()

    # Xác định xu hướng Chẵn hay Lẻ
    parity_result = "CHẴN (Chẵn Đầu / Chẵn Đuôi)" if chan_count >= le_count else "LẺ (Lẻ Đầu / Lẻ Đuôi)"

    return sorted_heads, sorted_tails, parity_result

def run_backtest_engine(region, start_date_str, total_days=10):
    try:
        start_dt = datetime.strptime(start_date_str, "%Y-%m-%d")
    except Exception:
        start_dt = datetime.now() - timedelta(days=10)
        
    total_days = max(1, min(40, total_days))
    region_name = "MIỀN BẮC" if region == 'mb' else ("MIỀN NAM" if region == 'mn' else "MIỀN TRUNG")
    
    header = f"🧪 BACKTEST {region_name} V67 (5 ĐẦU - 5 ĐUÔI - CHẴN/LẺ) - {total_days} KỲ TỪ: {start_date_str}\n\n"
    
    win_dau, win_duoi, win_chanle = 0, 0, 0
    valid_days_count = 0
    current_dt = start_dt
    
    history_lotes_buffer = []
    details = []
    
    pre_fill_dt = start_dt - timedelta(days=12)
    while pre_fill_dt < start_dt:
        p_str = pre_fill_dt.strftime("%Y-%m-%d")
        _, p_lotes = get_db_result(region, p_str)
        if p_lotes:
            history_lotes_buffer.append(p_lotes)
        pre_fill_dt += timedelta(days=1)

    for i in range(total_days):
        date_str = current_dt.strftime("%Y-%m-%d")
        
        if not is_date_already_drawn(date_str, region):
            break
            
        real_db, all_lotes = get_db_result(region, date_str)
        
        if real_db is not None:
            valid_days_count += 1
            
            top_heads, top_tails, predicted_parity = analyze_heads_tails_parity(region, history_lotes_buffer)
            
            real_dau = real_db[0]
            real_duoi = real_db[1]
            real_is_even = int(real_db) % 2 == 0
            pred_is_even = "CHẴN" in predicted_parity
            
            hit_dau = real_dau in top_heads
            hit_duoi = real_duoi in top_tails
            hit_chanle = (real_is_even == pred_is_even)
            
            if hit_dau: win_dau += 1
            if hit_duoi: win_duoi += 1
            if hit_chanle: win_chanle += 1
            
            if all_lotes:
                history_lotes_buffer.append(all_lotes)
            
            details.append(
                f"📅 {date_str} | ĐB Về: **{real_db}** (Thực tế)\n"
                f"├ Top 5 Đầu ({', '.join(top_heads)}): {'✅ NỔ' if hit_dau else '❌ XỊT'}\n"
                f"├ Top 5 Đuôi ({', '.join(top_tails)}): {'✅ NỔ' if hit_duoi else '❌ XỊT'}\n"
                f"└ Chẵn/Lẻ ({predicted_parity}): {'✅ NỔ' if hit_chanle else '❌ XỊT'}\n"
            )
        else:
            break
        
        current_dt += timedelta(days=1)
        
    footer = f"\n📊 **THỐNG KÊ HIỆU SUẤT V67:**\n• Số kỳ lấy được dữ liệu chuẩn: {valid_days_count}\n"
    if valid_days_count > 0:
        footer += f"• Top 5 Đầu: {win_dau}/{valid_days_count} ({round(win_dau*100/valid_days_count, 1)}%)\n"
        footer += f"• Top 5 Đuôi: {win_duoi}/{valid_days_count} ({round(win_duoi*100/valid_days_count, 1)}%)\n"
        footer += f"• Chẵn / Lẻ: {win_chanle}/{valid_days_count} ({round(win_chanle*100/valid_days_count, 1)}%)"
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
                "🤖 **XSMB - XSMN - XSMT MULTI-REGION BOT V67**\n\n"
                "📌 **Lệnh Dự Đoán:** `/dudoanmb`, `/dudoanmn`, `/dudoanmt`\n"
                "📌 **Lệnh Kiểm Thử:** `/testmb 2026-09-01=>15`, `/testmn`, `/testmt`\n"
                "📌 **Lệnh Hệ Thống:** `/reload`"
            )
            bot.reply_to(message, help_text, parse_mode="Markdown")

        @bot.message_handler(commands=['reload'])
        def handle_reload(message):
            reload_text = "🔄 **TẢI LẠI HỆ THỐNG V67 THÀNH CÔNG!**\n\n🚀 Đã chuyển đổi sang hệ thống phân tích Top 5 Đầu, Top 5 Đuôi & Cân bằng Chẵn/Lẻ."
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
                
            history_buffer = []
            check_dt = datetime.now() - timedelta(days=12)
            while check_dt < datetime.now():
                d_str = check_dt.strftime("%Y-%m-%d")
                _, lotes = get_db_result(region, d_str)
                if lotes:
                    history_buffer.append(lotes)
                check_dt += timedelta(days=1)
                
            top_heads, top_tails, parity = analyze_heads_tails_parity(region, history_buffer)
            
            res_msg = (
                f"🎯 **DỰ ĐOÁN GIẢI ĐẶC BIỆT {title} HÔM NAY** (V67)\n\n"
                f"📌 **Top 5 Đầu đề sáng nhất:**\n`{', '.join(top_heads)}`\n\n"
                f"📌 **Top 5 Đuôi đề sáng nhất:**\n`{', '.join(top_tails)}`\n\n"
                f"📌 **Dự đoán Chẵn / Lẻ:**\n`{parity}`"
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

        print("✅ Bot Telegram V67 đã khởi động thành công...", flush=True)
        bot.infinity_polling(timeout=60, long_polling_timeout=30)
    except Exception as e:
        print(f"💥 Lỗi khởi động Telegram Bot: {e}", flush=True)
        traceback.print_exc()

if __name__ == "__main__":
    print("🚀 Đang khởi động Web Server và Bot Engine V67...", flush=True)
    bot_thread = threading.Thread(target=run_telegram_bot)
    bot_thread.daemon = True
    bot_thread.start()

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)