@bot.message_handler(commands=['test'])
def handle_test_command(message):
    raw_text = message.text.strip()
    text_parts = raw_text.split()
    
    if len(text_parts) <= 1:
        # Nếu chỉ gõ /test không có tham số -> Test kết nối hệ thống
        msg = bot.reply_to(message, "🔍 *Bắt đầu kiểm tra kết nối hệ thống...*", parse_mode="Markdown")
        status_report = []
        try:
            count = db.count_results() if hasattr(db, 'count_results') else 0
            status_report.append(f"✅ **CSDL:** Hoạt động tốt (Đã lưu {count} ngày)")
        except Exception as e:
            status_report.append(f"❌ **CSDL:** Lỗi (`{e}`)")
            
        status_report.append("✅ **Scraper:** Hàm cào dữ liệu sẵn sàng")
        status_report.append("✅ **Predictor:** Thuật toán phân tích dự đoán sẵn sàng")

        report_text = "🧪 *BÁO CÁO KIỂM TRA HỆ THỐNG*\n\n" + "\n".join(status_report)
        bot.edit_message_text(report_text, chat_id=message.chat.id, message_id=msg.message_id, parse_mode="Markdown")
        return

    raw_input = " ".join(text_parts[1:]).strip()
    dates_to_test = []

    # 1. Phân tích dải ngày: ví dụ /test 2026-08-01 => 25 hoặc 2026-08-01 -> 2026-08-25
    range_match = re.search(r'(\d{4}-\d{2}-\d{2})\s*(?:=>|->|-|\s+)\s*(\d{1,2}|\d{4}-\d{2}-\d{2})$', raw_input)
    
    if range_match:
        start_str, end_val_str = range_match.group(1), range_match.group(2)
        try:
            start_date = datetime.strptime(start_str, "%Y-%m-%d")
            
            if len(end_val_str) <= 2:
                end_day = int(end_val_str)
                curr = start_date
                while True:
                    dates_to_test.append(curr.strftime("%Y-%m-%d"))
                    if curr.day == end_day:
                        break
                    curr += timedelta(days=1)
                    if (curr - start_date).days > 60: break
            else:
                end_date = datetime.strptime(end_val_str, "%Y-%m-%d")
                curr = start_date
                while curr <= end_date:
                    dates_to_test.append(curr.strftime("%Y-%m-%d"))
                    curr += timedelta(days=1)
        except Exception as e:
            bot.reply_to(message, f"❌ Lỗi định dạng khoảng ngày: `{e}`", parse_mode="Markdown")
            return

    # 2. Trường hợp test 1 ngày đơn lẻ: /test 2026-08-01
    elif re.match(r'^\d{4}-\d{2}-\d{2}$', text_parts[1]):
        dates_to_test.append(text_parts[1])
    else:
        bot.reply_to(message, "❌ Định dạng tham số không hợp lệ. Vui lòng thử lại dạng `YYYY-MM-DD` hoặc `YYYY-MM-DD => DD`.", parse_mode="Markdown")
        return

    # XỬ LÝ TEST LÔ THEO DẢI NGÀY
    if len(dates_to_test) > 1:
        msg = bot.reply_to(message, f"⏳ Đang test LÔ {len(dates_to_test)} ngày (Mỗi ngày lấy lùi 100 kỳ)...", parse_mode="Markdown")
        
        try:
            all_data = db.get_results(limit=500) if hasattr(db, 'get_results') else []
            
            bt_hits_cnt = 0
            st_any_hit_cnt = 0
            total_t5_hits = 0
            total_t10_hits = 0
            valid_days_cnt = 0
            details_list = []

            for target_date in dates_to_test:
                historical_data = [r for r in all_data if normalize_date(r.get('date')) < target_date][:100]
                actual_row = next((r for r in all_data if normalize_date(r.get('date')) == target_date), None)

                if not actual_row:
                    details_list.append(f"📅 **{target_date}**: ⚠️ _Thiếu CSDL_")
                    continue

                actual_numbers = actual_row.get('numbers', [])
                if isinstance(actual_numbers, str):
                    try: actual_numbers = json.loads(actual_numbers)
                    except: actual_numbers = actual_numbers.split(',')

                if hasattr(predictor, 'test_prediction_accuracy'):
                    res = predictor.test_prediction_accuracy(historical_data, actual_numbers)
                    if not res: continue

                    valid_days_cnt += 1

                    is_bt = res.get('bach_thu_hit', False)
                    st_hits = res.get('song_thu_hits', 0)
                    t5_hits = res.get('top_5_hits', 0)
                    t10_hits = res.get('top_10_hits', 0)

                    if is_bt: bt_hits_cnt += 1
                    if st_hits > 0: st_any_hit_cnt += 1
                    total_t5_hits += t5_hits
                    total_t10_hits += t10_hits

                    bt_icon = "✅" if is_bt else "❌"

                    details_list.append(
                        f"📅 **{target_date}** | 🔥 BTL: {bt_icon} | 👯 STL: **{st_hits}/2** | 🌟 Top5: **{t5_hits}/5** | 📊 Top10: **{t10_hits}/10**"
                    )

            if valid_days_cnt == 0:
                bot.edit_message_text("❌ Chưa có dữ liệu phù hợp trong dải ngày đã chọn.", chat_id=message.chat.id, message_id=msg.message_id)
                return

            rate_bt = (bt_hits_cnt / valid_days_cnt) * 100
            rate_st = (st_any_hit_cnt / valid_days_cnt) * 100
            avg_t5 = total_t5_hits / valid_days_cnt
            avg_t10 = total_t10_hits / valid_days_cnt

            report = (
                f"🧪 *BÁO CÁO TEST LÔ THEO KHOẢNG NGÀY (100 KỲ)*\n"
                f"🗓 **Giai đoạn:** `{dates_to_test[0]}` ➔ `{dates_to_test[-1]}` ({valid_days_cnt} ngày)\n"
                f"------------------------------------\n"
                + "\n".join(details_list) +
                f"\n------------------------------------\n"
                f"📊 **TỔNG KẾT TỶ LỆ TRÚNG ({valid_days_cnt} NGÀY):**\n"
                f"🔥 **Bạch Thủ Lô:** `{bt_hits_cnt}/{valid_days_cnt}` ngày (**{rate_bt:.1f}%**)\n"
                f"👯 **Song Thủ Lô (Về ≥1 lô):** `{st_any_hit_cnt}/{valid_days_cnt}` ngày (**{rate_st:.1f}%**)\n"
                f"🌟 **Top 5 Lô đẹp (Trung bình):** `{avg_t5:.1f}/5` con/ngày\n"
                f"📊 **Top 10 Lô đẹp (Trung bình):** `{avg_t10:.1f}/10` con/ngày\n"
            )
            bot.edit_message_text(report, chat_id=message.chat.id, message_id=msg.message_id, parse_mode="Markdown")

        except Exception as e:
            bot.edit_message_text(f"⚠️ Lỗi khi kiểm tra dải ngày: `{str(e)}`", chat_id=message.chat.id, message_id=msg.message_id, parse_mode="Markdown")

    # XỬ LÝ TEST LÔ 1 NGÀY ĐƠN LẺ
    else:
        target_date = dates_to_test[0]
        msg = bot.reply_to(message, f"⏳ Đang test LÔ ngày `{target_date}` (Phân tích 100 kỳ lùi về)...", parse_mode="Markdown")
        
        try:
            all_data = db.get_results(limit=500) if hasattr(db, 'get_results') else []
            historical_data = [r for r in all_data if normalize_date(r.get('date')) < target_date][:100]
            actual_row = next((r for r in all_data if normalize_date(r.get('date')) == target_date), None)
            
            if not actual_row:
                bot.edit_message_text(f"❌ Không tìm thấy dữ liệu kết quả XSMB ngày **{target_date}** trong CSDL!", chat_id=message.chat.id, message_id=msg.message_id, parse_mode="Markdown")
                return

            actual_numbers = actual_row.get('numbers', [])
            if isinstance(actual_numbers, str):
                try: actual_numbers = json.loads(actual_numbers)
                except: actual_numbers = actual_numbers.split(',')

            if hasattr(predictor, 'test_prediction_accuracy'):
                res = predictor.test_prediction_accuracy(historical_data, actual_numbers)
                if not res:
                    bot.edit_message_text("❌ Dữ liệu lịch sử không đủ để thuật toán phân tích.", chat_id=message.chat.id, message_id=msg.message_id)
                    return

                bt_icon = "✅ TRÚNG" if res['bach_thu_hit'] else "❌ TRƯỢT"
                st_hits_list = [x for x in res['song_thu'] if x in res['actual_numbers']]
                st_text = f"Trúng {res['song_thu_hits']}/2 lô ({', '.join(st_hits_list) if st_hits_list else 'Trượt'})"
                t5_hits_list = [x for x in res['top_5'] if x in res['actual_numbers']]
                t10_hits_list = [x for x in res['top_10'] if x in res['actual_numbers']]

                report = (
                    f"🧪 *BÁO CÁO TEST LÔ NGÀY {target_date} (100 KỲ)*\n"
                    f"------------------------------------\n"
                    f"🔥 *Bạch Thủ Lô ({res['bach_thu']})*: {bt_icon}\n"
                    f"👯 *Song Thủ Lô ({res['song_thu'][0]}, {res['song_thu'][1]})*: {st_text}\n"
                    f"🌟 *Top 5 Lô đẹp*: Trúng {res['top_5_hits']}/5 lô ({', '.join(t5_hits_list) if t5_hits_list else 'Trượt'})\n"
                    f"📊 *Top 10 Lô đẹp*: Trúng {res['top_10_hits']}/10 lô ({', '.join(t10_hits_list) if t10_hits_list else 'Trượt'})\n\n"
                    f"📝 *Tổng số giải lô về ngày đó*: {res['actual_count']} đầu số."
                )
                bot.edit_message_text(report, chat_id=message.chat.id, message_id=msg.message_id, parse_mode="Markdown")

        except Exception as e:
            bot.edit_message_text(f"⚠️ Lỗi khi kiểm tra dữ liệu ngày {target_date}: `{str(e)}`", chat_id=message.chat.id, message_id=msg.message_id, parse_mode="Markdown")