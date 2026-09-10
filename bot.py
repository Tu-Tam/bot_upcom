import os
import re
import sys
import random
import threading
import traceback
from collections import Counter
from flask import Flask
import telebot

# ==========================================
# 1. KHỞI TẠO WEB SERVER (MAIN THREAD FRIENDLY)
# ==========================================
app = Flask(__name__)

@app.route('/')
def home():
    return "Vietlott Bot V36 Engine: ONLINE", 200

@app.route('/health')
def health():
    return "OK", 200

# ==========================================
# 2. KIỂM TRA BOT TOKEN
# ==========================================
TOKEN = os.environ.get("BOT_TOKEN", "").strip()

# ==========================================
# 3. THUẬT TOÁN V36: ĐA DẠNG HÓA TOP 5 BỘ HẠT NHÂN
# ==========================================
def generate_v36_diverse_top5(history_data: list, game="645", seed_key=None) -> tuple:
    if seed_key:
        numeric_seed = int(re.sub(r'\D', '', str(seed_key))) if re.sub(r'\D', '', str(seed_key)) else 42
        random.seed(numeric_seed)

    is_655 = (str(game) == "655")
    max_num = 55 if is_655 else 45
    
    if history_data:
        all_draws = [d["result"] for d in history_data[-50:]]
        flat_nums = [n for d in all_draws for n in d]
        freq = Counter(flat_nums)
    else:
        freq = Counter()
    
    sorted_all = sorted(range(1, max_num + 1), key=lambda x: freq.get(x, 0), reverse=True)
    
    hot_pool = sorted_all[:15]
    warm_pool = sorted_all[15:30]
    cold_pool = sorted_all[30:]
    
    combos = []
    
    # Bộ 1: Hot Core
    c1 = sorted(random.sample(hot_pool, min(4, len(hot_pool))) + random.sample(warm_pool, min(2, len(warm_pool))))
    combos.append(c1)
    
    # Bộ 2: Balanced
    c2 = sorted(random.sample(hot_pool, 2) + random.sample(warm_pool, 2) + random.sample(cold_pool, 2))
    combos.append(c2)

    # Bộ 3: Cold Rebound
    c3 = sorted(random.sample(cold_pool, 3) + random.sample(hot_pool, 2) + random.sample(warm_pool, 1))
    combos.append(c3)

    # Bộ 4: Ten-Spread
    c4 = []
    tens_buckets = {}
    for n in range(1, max_num + 1):
        bucket = n // 10
        tens_buckets.setdefault(bucket, []).append(n)
        
    available_buckets = list(tens_buckets.keys())
    selected_buckets = random.sample(available_buckets, min(6, len(available_buckets)))
    for b in selected_buckets:
        c4.append(random.choice(tens_buckets[b]))
    c4 = sorted(c4)
    combos.append(c4)

    # Bộ 5: Matrix Random
    top_matrix = sorted(sorted_all[:28])
    c5 = sorted(random.sample(top_matrix, 6))
    combos.append(c5)

    return combos, top_matrix

# ==========================================
# 4. KHỞI CHẠY BOT TELEGRAM TRONG THREAD
# ==========================================
def run_telegram_bot():
    if not TOKEN or TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("\n⚠️ CHƯA CẤU HÌNH 'BOT_TOKEN' TRÊN RENDER! Vui lòng thêm Environment Variable.\n", flush=True)
        return

    bot = telebot.TeleBot(TOKEN)

    @bot.message_handler(commands=['start', 'help'])
    def send_welcome(message):
        help_text = (
            "🤖 **VIETLOTT BOT V36 ENGINE**\n\n"
            "Cú pháp lệnh:\n"
            "• `/dudoan 645` - Dự đoán Mega 6/45 (5 bộ đa dạng)\n"
            "• `/dudoan 655` - Dự đoán Power 6/55 (5 bộ đa dạng)"
        )
        bot.reply_to(message, help_text, parse_mode="Markdown")

    @bot.message_handler(commands=['dudoan'])
    def handle_dudoan(message):
        try:
            args = message.text.split()
            game = args[1] if len(args) > 1 else "645"
            combos, _ = generate_v36_diverse_top5([], game=game, seed_key=message.message_id)
            
            res_msg = f"🎯 **DỰ ĐOÁN TOP 5 BỘ HẠT NHÂN V36 ({'Power 6/55' if game=='655' else 'Mega 6/45'})**\n\n"
            strategies = [
                "🔥 Bộ 1 (Hot Core)",
                "⚖️ Bộ 2 (Balanced)",
                "❄️ Bộ 3 (Cold Rebound)",
                "🌐 Bộ 4 (Ten-Spread)",
                "🎲 Bộ 5 (Matrix Random)"
            ]
            for strat, combo in zip(strategies, combos):
                res_msg += f"{strat}:\n`{combo}`\n\n"
                
            bot.reply_to(message, res_msg, parse_mode="Markdown")
        except Exception as e:
            bot.reply_to(message, f"❌ Lỗi xử lý: {str(e)}")

    print("✅ Bot Telegram đã chạy và đang lắng nghe...", flush=True)
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=30)
    except Exception as e:
        print(f"💥 Lỗi Bot Polling: {e}", flush=True)

# ==========================================
# 5. EXECUTION ENTRY POINT
# ==========================================
if __name__ == "__main__":
    print("🚀 Đang khởi động hệ thống Vietlott Engine...", flush=True)
    
    # Chạy Telegram Bot ở background thread
    bot_thread = threading.Thread(target=run_telegram_bot)
    bot_thread.daemon = True
    bot_thread.start()

    # Chạy Web Server ở main thread để Render binding PORT ngay lập tức
    port = int(os.environ.get("PORT", 10000))
    print(f"🌐 Web Server đang mở cổng {port}...", flush=True)
    app.run(host="0.0.0.0", port=port)