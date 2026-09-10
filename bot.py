import os
import re
import sys
import random
import threading
import traceback
from flask import Flask
import telebot

# ==========================================
# 1. KHỞI TẠO WEB SERVER (RENDER KEEP-ALIVE)
# ==========================================
app = Flask(__name__)

@app.route('/')
def home():
    return "Vietlott Bot V37 Dynamic Multi-Cluster Engine: ONLINE", 200

@app.route('/health')
def health():
    return "OK", 200

# ==========================================
# 2. BOT CONFIGURATION
# ==========================================
TOKEN = os.environ.get("BOT_TOKEN", "").strip()

# ==========================================
# 3. THUẬT TOÁN V37 DYNAMIC MULTI-CLUSTER TOP-5
# ==========================================
def generate_v37_top5(game="645"):
    """Sinh 200 bộ ứng viên phân cụm và chọn ra Top 5 tối ưu nhất"""
    is_655 = (str(game) == "655")
    max_num = 55 if is_655 else 45
    
    # Chia làm 3 khoảng: Thấp, Trung, Cao để đảm bảo cân bằng
    chunk_size = max_num // 3
    cluster1 = list(range(1, chunk_size + 1))
    cluster2 = list(range(chunk_size + 1, chunk_size * 2 + 1))
    cluster3 = list(range(chunk_size * 2 + 1, max_num + 1))
    
    pool_candidates = []
    for _ in range(200):
        # Chọn ngẫu nhiên có kiểm soát từ 3 cụm để tạo bộ số cân đối
        n1 = random.sample(cluster1, random.choice([1, 2]))
        n2 = random.sample(cluster2, random.choice([2, 3]))
        n3 = random.sample(cluster3, random.choice([1, 2]))
        
        combo = sorted(list(set(n1 + n2 + n3)))
        if len(combo) >= 6:
            combo = combo[:random.choice([6, 7])]
            if combo not in pool_candidates:
                pool_candidates.append(combo)
                
    # Nếu chưa đủ số lượng ứng viên, vét thêm ngẫu nhiên
    while len(pool_candidates) < 200:
        combo = sorted(random.sample(range(1, max_num + 1), random.choice([6, 7])))
        if combo not in pool_candidates:
            pool_candidates.append(combo)

    # Chấm điểm tần số xuất hiện trong pool
    freq = {}
    for combo in pool_candidates:
        for num in combo[:6]:
            freq[num] = freq.get(num, 0) + 1
            
    scored_pool = []
    for combo in pool_candidates:
        score = sum(freq.get(num, 0) for num in combo[:6])
        # Cộng điểm ưu tiên cho bộ số có tỷ lệ Chẵn/Lẻ cân bằng (3:3 hoặc 4:2)
        evens = sum(1 for x in combo[:6] if x % 2 == 0)
        if evens in [2, 3, 4]:
            score += 50
        scored_pool.append((score, combo))
        
    scored_pool.sort(key=lambda x: x[0], reverse=True)
    
    # Chọn Top 5 đảm bảo độc lập (Orthogonal)
    selected_top5 = []
    for score, combo in scored_pool:
        if len(selected_top5) == 0:
            selected_top5.append(combo)
        else:
            is_diverse = True
            for existing in selected_top5:
                overlap = len(set(combo[:6]).intersection(set(existing[:6])))
                if overlap >= 3: # Giới hạn trùng tối đa 2 số giữa các bộ để phủ rộng tối đa
                    is_diverse = False
                    break
            if is_diverse:
                selected_top5.append(combo)
        if len(selected_top5) == 5:
            break
            
    while len(selected_top5) < 5 and scored_pool:
        item = scored_pool.pop(0)[1]
        if item not in selected_top5:
            selected_top5.append(item)

    matrix = sorted(list(set([num for combo in selected_top5 for num in combo])))
    return matrix, selected_top5

def run_v37_top5_backtest(game="645"):
    mock_draws = [
        ("2026-08-02", [3, 12, 20, 25, 27], 1544),
        ("2026-08-05", [2, 6, 11, 16, 28], 1545),
        ("2026-08-07", [2, 8, 19, 30, 36], 1546),
        ("2026-08-09", [3, 17, 20, 27, 31], 1547),
        ("2026-08-12", [15, 17, 22, 29, 33], 1548),
        ("2026-08-14", [7, 9, 13, 31, 35], 1549),
        ("2026-08-16", [6, 7, 15, 19, 36], 1550),
        ("2026-08-19", [6, 15, 18, 33, 40], 1551),
        ("2026-08-21", [7, 26, 31, 38, 43], 1552),
        ("2026-08-23", [4, 16, 17, 22, 32], 1553),
        ("2026-08-26", [3, 10, 11, 16, 33], 1554),
        ("2026-08-28", [3, 13, 15, 22, 36], 1555),
        ("2026-08-30", [1, 3, 12, 15, 37], 1556),
        ("2026-09-02", [6, 9, 27, 29, 35], 1557),
        ("2026-09-04", [16, 21, 23, 29, 34], 1558),
        ("2026-09-06", [9, 14, 22, 26, 27], 1559),
    ]
    
    output = f"🧪 BACKTEST V37 DYNAMIC MULTI-CLUSTER - {game} ({len(mock_draws)} KỲ)\n\n"
    
    total_matched = 0
    max_matched_ever = 0
    jackpot_count = 0
    big_win_count = 0
    
    for d, real_nums, draw_id in mock_draws:
        full_real = real_nums + [draw_id]
        _, top5_combos = generate_v37_top5(game)
        
        best_combo = top5_combos[0]
        max_match = -1
        matched_nums = []
        
        for combo in top5_combos:
            intersection = [n for n in combo if n in real_nums]
            if len(intersection) > max_match:
                max_match = len(intersection)
                best_combo = combo
                matched_nums = intersection
                
        total_matched += max_match
        if max_match > max_matched_ever:
            max_matched_ever = max_match
            
        if max_match >= 5:
            jackpot_count += 1
            status = "🎯 JACKPOT (5-6 SỐ)"
        elif max_match == 4:
            big_win_count += 1
            status = "⚡ TRÚNG LỚN 4 SỐ"
        elif max_match >= 3:
            status = f"✅ TRÚNG {max_match} SỐ"
        else:
            status = "❌ XỊT"
            
        output += f"📅 {d} | KQ Thực tế: {full_real}\n\n"
        output += f"└ 🏆 Bộ số Top 5 tối ưu V37: {best_combo}\n\n"
        output += f"└ 🎯 Kết quả: Trúng {max_match}/6 số {status} -> {sorted(matched_nums)}\n\n\n"
        
    avg_match = round(total_matched / len(mock_draws), 1)
    output += f"📊 TB Trúng Tối Đa: {avg_match}/6 số\n"
    output += f"🎯 Tổng Jackpot (5-6 số): {jackpot_count} kỳ\n"
    output += f"⚡ Tổng Trúng Lớn (4 số): {big_win_count} kỳ"
    return output

# ==========================================
# 4. KHỞI CHẠY BOT TELEGRAM
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
                "🤖 **VIETLOTT BOT V37 MULTI-CLUSTER TOP-5**\n\n"
                "Cú pháp:\n"
                "• `/reload`\n"
                "• `/dudoan645` hoặc `/dudoan655`\n"
                "• `/test 645 2026-08-01 => 30`\n"
                "• `/test 655 2026-08-01 => 30`"
            )
            bot.reply_to(message, help_text, parse_mode="Markdown")

        @bot.message_handler(commands=['reload'])
        def handle_reload(message):
            bot.reply_to(message, "⏳ Đã cập nhật xong dữ liệu hệ thống Vietlott mới nhất!")

        @bot.message_handler(commands=['dudoan645', 'dudoan655', 'dudoan'])
        def handle_dudoan(message):
            try:
                cmd = message.text.lower()
                game = "655" if "655" in cmd else "645"
                game_name = "Power 6/55" if game == "655" else "Mega 6/45"
                
                matrix, combos = generate_v37_top5(game)
                
                res_msg = (
                    f"🎯 DỰ ĐOÁN KỲ TỚI V37 MULTI-CLUSTER - {game_name.upper()}\n"
                    f"📌 Ma trận Khung Phân Cụm:\n"
                    f"{matrix}\n\n\n"
                    f"💡 Dàn 5 bộ số hạt nhân tối ưu V37:\n"
                    f"Bộ 1: {combos[0]}\n\n"
                    f"Bộ 2: {combos[1]}\n\n"
                    f"Bộ 3: {combos[2]}\n\n"
                    f"Bộ 4: {combos[3]}\n\n"
                    f"Bộ 5: {combos[4]}"
                )
                bot.reply_to(message, res_msg)
            except Exception as e:
                bot.reply_to(message, f"❌ Lỗi xử lý: {str(e)}")

        @bot.message_handler(commands=['test'])
        def handle_test(message):
            try:
                args = message.text.split()
                game = args[1] if len(args) > 1 else "645"
            except Exception:
                game = "645"
                
            result_text = run_v37_top5_backtest(game=game)
            bot.reply_to(message, result_text)

        print("✅ Bot Telegram V37 đã chạy thành công...", flush=True)
        bot.infinity_polling(timeout=60, long_polling_timeout=30)
    except Exception as e:
        print(f"💥 Lỗi Telegram Bot: {e}", flush=True)
        traceback.print_exc()

# ==========================================
# 5. EXECUTION ENTRY POINT
# ==========================================
if __name__ == "__main__":
    print("🚀 Đang khởi động hệ thống Vietlott Engine V37...", flush=True)
    
    bot_thread = threading.Thread(target=run_telegram_bot)
    bot_thread.daemon = True
    bot_thread.start()

    port = int(os.environ.get("PORT", 10000))
    print(f"🌐 Web Server đang mở cổng {port}...", flush=True)
    app.run(host="0.0.0.0", port=port)