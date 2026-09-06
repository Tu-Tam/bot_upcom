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

def parse_date_range(raw_text: str, dataset: list) -> list:
    """Tách chuẩn mốc ngày và số kỳ quay N (ví dụ: => 30)"""
    clean_text = re.sub(r'^(655|645)', '', raw_text).strip()
    
    match = re.search(r'(\d{4}-\d{2}-\d{2})\s*(?:=>|->|-|\s+)\s*(\d{1,3}|\d{4}-\d{2}-\d{2})$', clean_text)
    
    if not match:
        single_date = re.search(r'(\d{4}-\d{2}-\d{2})', clean_text)
        if single_date:
            dt_str = single_date.group(1)
            return [d["date"] for d in dataset if d["date"] == dt_str]
        return []

    start_str, end_val = match.group(1), match.group(2)
    future_draws = [d["date"] for d in dataset if d["date"] >= start_str]
    
    if not future_draws:
        return []

    if end_val.isdigit():
        return future_draws[:int(end_val)]
    else:
        return [dt for dt in future_draws if dt <= end_val]

@bot.message_handler(commands=['start', 'help'])
def send_welcome(msg):
    text = (
        "🧪 **BOT HYBRID VIETLOTT MULTI-GAME**\n\n"
        "📌 **Power 6/55:**\n`/test 655 2026-08-01 => 30`\n`/dudoan 655`\n\n"
        "📌 **Mega 6/45:**\n`/test 645 2026-08-01 => 30`\n`/dudoan 645`"
    )
    bot.reply_to(msg, text, parse_mode="Markdown")

@bot.message_handler(commands=['reload'])
def handle_reload(msg):
    d655 = fetch_vietlott_655_data()
    d645 = fetch_vietlott_645_data()
    bot.reply_to(msg, f"🔄 **Đã cập nhật CSDL:**\n- Power 6/55: `{len(d655)} kỳ`\n- Mega 6/45: `{len(d645)} kỳ`", parse_mode="Markdown")

@bot.message_handler(commands=['test'])
def handle_test(msg):
    raw_text = msg.text.replace('/test', '').strip()
    
    game = "645" if "645" in raw_text else "655"
    predict_fn = predict_mega_645_hybrid_10 if game == "645" else predict_power_655_hybrid_10

    raw_dataset = get_dataset(game)
    if not raw_dataset:
        raw_dataset = fetch_vietlott_645_data() if game == "645" else fetch_vietlott_655_data()

    if not raw_dataset:
        bot.reply_to(msg, "❌ Không thể lấy dữ liệu CSDL.", parse_mode="Markdown")
        return

    # Chuẩn hóa ngày về YYYY-MM-DD
    for d in raw_dataset:
        if "/" in d["date"]:
            parts = d["date"].split("/")
            if len(parts) == 3:
                d["date"] = f"{parts[2]}-{int(parts[1]):02d}-{int(parts[0]):02d}"

    sorted_dataset = sorted(raw_dataset, key=lambda x: x["date"])
    dates = parse_date_range(raw_text, sorted_dataset)
    
    if not dates:
        bot.reply_to(msg, f"❌ Không tìm thấy dữ liệu kỳ quay phù hợp.\n*(CSDL hiện có từ: `{sorted_dataset[0]['date']}` đến `{sorted_dataset[-1]['date']}`)*", parse_mode="Markdown")
        return

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
        bot.reply_to(msg, "❌ Không thể thực hiện backtest cho dải kỳ quay này.", parse_mode="Markdown")

@bot.message_handler(commands=['dudoan'])
def handle_dudoan(msg):
    raw_text = msg.text.replace('/dudoan', '').strip()
    game = "645" if "645" in raw_text else "655"
    predict_fn = predict_mega_645_hybrid_10 if game == "645" else predict_power_655_hybrid_10

    raw_dataset = get_dataset(game)
    if not raw_dataset:
        raw_dataset = fetch_vietlott_645_data() if game == "645" else fetch_vietlott_655_data()

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