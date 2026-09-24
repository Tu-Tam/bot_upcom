def run_backtest_engine(region, start_date_str, total_days=10):
    try:
        start_dt = datetime.strptime(start_date_str, "%Y-%m-%d")
    except Exception:
        start_dt = datetime.now() - timedelta(days=10)
        
    total_days = max(1, min(31, total_days)) # Cho phép test tối đa 31 ngày mà vẫn hiện chi tiết
    region_name = "MIỀN BẮC" if region == 'mb' else ("MIỀN NAM" if region == 'mn' else "MIỀN TRUNG")
    
    output = f"🧪 BACKTEST {region_name} V55 (CÀO WEB THỰC TẾ) - {total_days} KỲ TỪ: {start_date_str}\n\n"
    
    win_30, win_40, win_50 = 0, 0, 0
    valid_days_count = 0
    current_dt = start_dt
    
    for i in range(total_days):
        date_str = current_dt.strftime("%Y-%m-%d")
        real_db = fetch_lottery_result(region, date_str)
        
        if real_db is not None:
            valid_days_count += 1
            dan_30 = generate_dan_so(30)
            dan_40 = generate_dan_so(40)
            dan_50 = generate_dan_so(50)
            
            hit_30 = real_db in dan_30
            hit_40 = real_db in dan_40
            hit_50 = real_db in dan_50
            
            if hit_30: win_30 += 1
            if hit_40: win_40 += 1
            if hit_50: win_50 += 1
            
            # ĐÃ ĐỒNG BỘ: Luôn hiển thị chi tiết từng ngày cho mọi lệnh test
            output += f"📅 {date_str} | ĐB Về: **{real_db}** (Thực tế)\n"
            output += f"├ Dàn 30 số: {'✅ NỔ' if hit_30 else '❌ XỊT'}\n"
            output += f"├ Dàn 40 số: {'✅ NỔ' if hit_40 else '❌ XỊT'}\n"
            output += f"└ Dàn 50 số: {'✅ NỔ' if hit_50 else '❌ XỊT'}\n\n"
        else:
            output += f"📅 {date_str} | ⚠️ Không cào được dữ liệu thực tế từ web\n\n"
        
        current_dt += timedelta(days=1)
        
    output += f"📊 **THỐNG KÊ HIỆU SUẤT (Dựa trên dữ liệu cào thật):**\n"
    output += f"• Số kỳ lấy được dữ liệu: {valid_days_count}/{total_days}\n"
    if valid_days_count > 0:
        output += f"• Dàn 30 số: {win_30}/{valid_days_count} ({round(win_30*100/valid_days_count, 1)}%)\n"
        output += f"• Dàn 40 số: {win_40}/{valid_days_count} ({round(win_40*100/valid_days_count, 1)}%)\n"
        output += f"• Dàn 50 số: {win_50}/{valid_days_count} ({round(win_50*100/valid_days_count, 1)}%)"
    else:
        output += f"• Không có dữ liệu hợp lệ để tính toán hiệu suất."
        
    return output