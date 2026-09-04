import os, sys, time, threading, re, copy
from datetime import datetime, timedelta
import telebot
from flask import Flask
from vietlott_scraper import fetch_vietlott_655_data, get_dataset
from analytics import predict_power_655_hybrid_10

TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    sys.exit(1)

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

@app.route('/')
def home(): 
    return "Bot Vietlott Power 6/55 đang hoạt động!", 200

def run_flask():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

def parse_date_range(raw_input: str) -> list:
    dates_to_test = []
    clean_text = raw_input.replace('655', '').strip()
    range_match = re.search(r'(\d{4}-\d{2}-\d{2})\s*(?:=>|->|-|\s+)\s*(\d{1,2}|\d{4}-\d{2}-\d{2})$', clean_text)
    if range_match:
        start_str, end_val_str = range_match.group(1), range_match.group(2)
        start_date = datetime.strptime(start_str, "%Y-%m-%d")
        if len(end_val_str) <= 2:
            end_day = int(end_val_str)
            curr = start_date
            while True:
                if curr.weekday() in [1, 3, 5]: dates_to_test.append(curr.strftime("%Y-%m-%d"))
                if curr.day == end_day: break
                curr += timedelta(days=1)
                if (curr - start_date).days > 60: break
        else:
            end_date = datetime.strptime(end_val_str, "%Y-%m-%d")
            curr = start_date
            while curr <= end_date:
                if curr.weekday() in [1, 3, 5]: dates_to_test.append(curr.strftime("%Y-%m-%d"))
                curr += timedelta(days=1)
    elif re.match(r'^\d{4}-\d{2}-\d{2}$', clean_text):
        dates_to_test.append(clean_text)
    return dates_to_test

@bot.message_handler(commands=['start', 'help'])
def send_welcome(msg):
    bot.reply_to(msg, "🧪 **BOT HYBRID POWER 6/55**\n`/test 655 2026-08-01 => 29`\n`/dudoan`", parse_mode="Markdown")

@bot.message_handler(commands=['reload'])
def handle_reload(msg):
    bot.reply_to(msg, f"🔄 Tổng kỳ quay: `{fetch_vietlott_655_data()}`", parse_mode="Markdown")

@bot.message_handler(commands=['test'])
def handle_test(msg):
    dates = parse_date_range(msg.text.replace('/test', '').strip())
    
    # Lấy dataset và sắp xếp chuẩn CŨ -> MỚI
    raw_dataset = get_dataset()
    sorted_dataset = sorted(raw_dataset, key=lambda x: x["date"])
    
    details, total_matched = [], 0

    for dt in dates:
        actual = next((d for d in sorted_dataset if d["date"] == dt), None)
        if not actual: continue
        
        # Dùng copy.deepcopy để cách ly hoàn toàn danh sách quá khứ
        past = [copy.deepcopy(d) for d in sorted_dataset if d["date"] < dt]
        if not past: continue
        
        # Dự đoán dàn số từ dữ liệu quá khứ chuẩn
        pred = predict_power_655_hybrid_10(past)
        matched = set(pred).intersection(set(actual["result"]))
        total_matched += len(matched)
        
        icon = "🔥" if len(matched) >= 5 else ("✅" if len(matched) >= 3 else "❌")
        matched_str = ','.join(map(str, sorted(list(matched))))
        details.append(f"📅 **{dt}**: Trùng **{len(matched)}/6** {icon} `[{matched_str}]`")

    if details:
        res = f"🧪 *BACKTEST HYBRID ({len(details)} KỲ)*\n" + "\n".join(details) + f"\n\n📊 TB: `{(total_matched/len(details)):.1f}/6` số"
        bot.reply_to(msg, res, parse_mode="Markdown")
    else:
        bot.reply_to(msg, "❌ Không tìm thấy dữ liệu kỳ quay phù hợp.", parse_mode="Markdown")

@bot.message_handler(commands=['dudoan'])
def handle_dudoan(msg):
    raw_dataset = get_dataset()
    sorted_dataset = sorted(raw_dataset, key=lambda x: x["date"])
    dan_10 = predict_power_655_hybrid_10(sorted_dataset)
    bot.reply_to(msg, f"🎯 **Dàn 10 Hybrid:**\n`[{', '.join(map(str, dan_10))}]`", parse_mode="Markdown")

if __name__ == '__main__':
    fetch_vietlott_655_data()
    threading.Thread(target=run_flask, daemon=True).start()
    
    try:
        bot.remove_webhook()
        time.sleep(1)
    except Exception as e:
        pass

    while True:
        try:
            bot.infinity_polling(skip_pending=True, timeout=20, long_polling_timeout=10)
        except Exception as e:
            time.sleep(5)