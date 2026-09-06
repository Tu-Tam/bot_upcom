import os, sys, time, threading, re, copy
from datetime import datetime, timedelta
import telebot
from flask import Flask
from vietlott_scraper import fetch_vietlott_655_data, fetch_vietlott_645_data, get_dataset
from analytics import predict_power_655_hybrid_10, predict_mega_645_hybrid_10

TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    sys.exit(1)

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

@app.route('/')
def home(): 
    return "Bot Vietlott Multi-Game đang hoạt động!", 200

def run_flask():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

def parse_date_range(raw_input: str, dataset: list) -> list:
    clean_text = re.sub(r'^(655|645)', '', raw_input).strip()
    if not clean_text:
        return []

    range_match = re.search(r'(\d{4}-\d{2}-\d{2})\s*(?:=>|->|-|\s+)\s*(\d{1,2}|\d{4}-\d{2}-\d{2})$', clean_text)
    available_dates = sorted(list(set(d["date"] for d in dataset)))

    if range_match:
        start_str, end_val_str = range_match.group(1), range_match.group(2)
        future_dates = [d for d in available_dates if d >= start_str]
        
        if not future_dates:
            return []

        if len(end_val_str) <= 2 and int(end_val_str) > 0:
            return future_dates[:int(end_val_str)]
        else:
            return [d for d in future_dates if d <= end_val_str]

    elif re.match(r'^\d{4}-\d{2}-\d{2}$', clean_text):
        return [clean_text] if clean_text in available_dates else []

    return []

@bot.message_handler(commands=['start', 'help'])
def send_welcome(msg):
    text = (
        "🧪 **BOT HYBRID VIETLOTT MULTI-GAME**\n\n"
        "📌 **Power 6/55:**\n`/test 655 2026-08-01 => 20`\n`/dudoan 655`\n\n"
        "📌 **Mega 6/45:**\n`/test 645 2026-08-01 => 20`\n`/dudoan 645`"
    )
    bot.reply_to(msg, text, parse_mode="Markdown")

@bot.message_handler(commands=['reload'])
def handle_reload(msg):
    d655 = fetch_vietlott_655_data()
    d645 = fetch_vietlott_645_data()
    bot.reply_to(msg, f"🔄 **Đã cập nhật dữ liệu:**\n- Power 6/55: `{len(d655)} kỳ`\n- Mega 6/45: `{len(d645)} kỳ`", parse_mode="Markdown")

@bot.message_handler(commands=['test'])
def handle_test(msg):
    raw_text = msg.text.replace('/test', '').strip()
    
    # Nhận diện giải (mặc định 655)
    game = "645" if "645" in raw_text else "655"
    predict_fn = predict_mega_645_hybrid_10 if game == "645" else predict_power_655_hybrid_10

    raw_dataset = get_dataset(game)
    sorted_dataset = sorted(raw_dataset, key=lambda x: x["date"])

    dates = parse_date_range(raw_text, sorted_dataset)
    details, total_matched = [], 0

    for dt in dates:
        actual = next((d for d in sorted_dataset if d["date"] == dt), None)
        if not actual: continue
        
        past = [copy.deepcopy(d) for d in sorted_dataset if d["date"] < dt]
        if not past: continue
        
        pred = predict_fn(past)
        matched = set(pred).intersection(set(actual["result"]))
        total_matched += len(matched)
        
        icon = "🔥" if len(matched) >= 5 else ("✅" if len(matched) >= 3 else "❌")
        matched_str = ','.join(map(str, sorted(list(matched))))
        details.append(f"📅 **{dt}**: Trùng **{len(matched)}/6** {icon} `[{matched_str}]`")

    if details:
        res = f"🧪 *BACKTEST HYBRID {game} ({len(details)} KỲ)*\n" + "\n".join(details) + f"\n\n📊 TB: `{(total_matched/len(details)):.1f}/6` số"
        bot.reply_to(msg, res, parse_mode="Markdown")
    else:
        bot.reply_to(msg, "❌ Không tìm thấy dữ liệu kỳ quay phù hợp.", parse_mode="Markdown")

@bot.message_handler(commands=['dudoan'])
def handle_dudoan(msg):
    raw_text = msg.text.replace('/dudoan', '').strip()
    game = "645" if "645" in raw_text else "655"
    predict_fn = predict_mega_645_hybrid_10 if game == "645" else predict_power_655_hybrid_10

    raw_dataset = get_dataset(game)
    sorted_dataset = sorted(raw_dataset, key=lambda x: x["date"])
    dan_10 = predict_fn(sorted_dataset)
    bot.reply_to(msg, f"🎯 **Dàn 10 Hybrid Vietlott {game}:**\n`[{', '.join(map(str, dan_10))}]`", parse_mode="Markdown")

if __name__ == '__main__':
    fetch_vietlott_655_data()
    fetch_vietlott_645_data()
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