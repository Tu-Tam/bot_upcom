import requests
import time
from datetime import datetime, timedelta
from database import save_result, count_results

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
}

# Cấu hình endpoint cho các giải Vietlott
VIETLOTT_ENDPOINTS = {
    "655": "https://voh.com.vn/api/v1/lottery/vietlott/power-6-55",
    "645": "https://voh.com.vn/api/v1/lottery/vietlott/mega-6-45",
    "3d": "https://voh.com.vn/api/v1/lottery/vietlott/max-3d",
    "keno": "https://voh.com.vn/api/v1/lottery/vietlott/keno"
}

def lay_ket_qua_ngay(game_type, date_str):
    """
    Cào kết quả Vietlott theo game_type và date_str (Định dạng YYYY-MM-DD)
    """
    if game_type not in VIETLOTT_ENDPOINTS:
        return None

    try:
        url = f"{VIETLOTT_ENDPOINTS[game_type]}?date={date_str}"
        response = requests.get(url, headers=HEADERS, timeout=7)
        
        if response.status_code != 200:
            return None

        data = response.json()
        
        # Xử lý bóc tách mảng số từ JSON trả về
        if data and "data" in data and "results" in data["data"]:
            raw_results = data["data"]["results"]
            
            # Đảm bảo dữ liệu trả về dạng danh sách số nguyên hoặc chuỗi số chuẩn
            numbers = []
            for item in raw_results:
                try:
                    numbers.append(int(item))
                except (ValueError, TypeError):
                    continue

            # Kiểm tra tính hợp lệ số lượng bóng/số của từng giải
            if game_type in ["655", "645"] and len(numbers) >= 6:
                return numbers[:6]
            elif game_type == "3d" and len(numbers) >= 3:
                return numbers[:3]
            elif game_type == "keno" and len(numbers) >= 20:
                return numbers[:20]

        return None
    except Exception:
        return None

def scrape_past_days(days=365):
    """
    Quét dữ liệu lịch sử X ngày cho toàn bộ các giải Vietlott (655, 645, 3d, keno)
    """
    print(f"🚀 Bắt đầu quét dữ liệu lịch sử {days} ngày cho toàn bộ giải Vietlott...", flush=True)
    start_date = datetime.now() - timedelta(days=1)
    games = ["655", "645", "3d", "keno"]
    thanh_cong = 0

    for i in range(days):
        current_date = (start_date - timedelta(days=i)).strftime("%Y-%m-%d")
        
        for game in games:
            data = lay_ket_qua_ngay(game, current_date)
            if data:
                save_result(game, current_date, data)
                thanh_cong += 1
                print(f"  └─ ✅ [{i+1}/{days}] Giải {game.upper()} - Ngày {current_date}: Đã lưu {len(data)} số", flush=True)

        time.sleep(0.2)

    print(f"🎉 Hoàn tất! Đã lưu tổng cộng {thanh_cong} bản ghi vào CSDL.", flush=True)
    return count_results()

def scrape_today():
    """
    Cào kết quả các giải Vietlott cho ngày hôm nay
    """
    today_str = datetime.now().strftime("%Y-%m-%d")
    games = ["655", "645", "3d", "keno"]
    has_success = False

    for game in games:
        data = lay_ket_qua_ngay(game, today_str)
        if data:
            save_result(game, today_str, data)
            has_success = True
        else:
            # Nếu hôm nay chưa quay, thử kiểm tra ngày hôm qua
            yesterday_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            data_yesterday = lay_ket_qua_ngay(game, yesterday_str)
            if data_yesterday:
                save_result(game, yesterday_str, data_yesterday)
                
    return has_success

# Alias giữ tính tương thích với cấu trúc mã nguồn cũ
tai_90_ngay_gan_nhat = scrape_past_days
