import requests
import json
import os

# API Endpoint
URL_655_POST = "https://vietlott.vn/api/front/v1/draw-result/power655"
URL_645_POST = "https://vietlott.vn/api/front/v1/draw-result/mega645"

# Nguồn GET dự phòng (Tránh bị Render IP block)
URL_655_GET = "https://vietlott.vn/vi/trung-thuong/ket-qua-truc-tiep/power-655"
URL_645_GET = "https://vietlott.vn/vi/trung-thuong/ket-qua-truc-tiep/mega-645"

DATA_FILE_655 = "vietlott_655.json"
DATA_FILE_645 = "vietlott_645.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "Origin": "https://vietlott.vn",
    "Referer": "https://vietlott.vn/"
}

def fetch_vietlott_655_data(limit=300):
    return _fetch_with_fallback(URL_655_POST, DATA_FILE_655, limit, "655")

def fetch_vietlott_645_data(limit=300):
    return _fetch_with_fallback(URL_645_POST, DATA_FILE_645, limit, "645")

def _fetch_with_fallback(url_post, filename, limit, game_type):
    # Lần 1: Thử POST API
    data = _post_api(url_post, limit)
    
    # Lần 2: Nếu POST bị chặn (trả về rỗng), thử dùng phương thức POST không Header Origin
    if not data:
        data = _post_api_simple(url_post, limit)

    if data:
        # Sắp xếp CŨ -> MỚI
        data.sort(key=lambda x: x["date"])
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return data

    # Nếu không lấy được dữ liệu mới nhưng đã có file cũ thì giữ nguyên file cũ
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
            
    return []

def _post_api(url, limit):
    try:
        session = requests.Session()
        payload = {"pageIndex": 1, "pageSize": limit}
        response = session.post(url, json=payload, headers=HEADERS, timeout=15)
        
        if response.status_code == 200:
            res_json = response.json()
            draw_list = res_json.get("result", []) or res_json.get("listResults", [])
            return _parse_draw_list(draw_list)
    except Exception as e:
        print(f"Lỗi POST API {url}: {e}")
    return []

def _post_api_simple(url, limit):
    try:
        simple_headers = {"User-Agent": "Mozilla/5.0"}
        payload = {"pageIndex": 1, "pageSize": limit}
        response = requests.post(url, json=payload, headers=simple_headers, timeout=10)
        if response.status_code == 200:
            res_json = response.json()
            draw_list = res_json.get("result", []) or res_json.get("listResults", [])
            return _parse_draw_list(draw_list)
    except Exception as e:
        print(f"Lỗi Simple POST {url}: {e}")
    return []

def _parse_draw_list(draw_list):
    formatted_data = []
    for item in draw_list:
        res_str = item.get("result", "") or item.get("drawResult", "") or item.get("numbers", "")
        date_raw = item.get("drawDate", "") or item.get("periodDate", "") or item.get("date", "")
        
        if not res_str or not date_raw:
            continue
        
        # Bóc tách dãy số
        raw_nums = res_str.split("|")[0].split(",")
        numbers = [int(x) for x in raw_nums if x.strip().isdigit()]
        
        # Chuẩn hóa định dạng YYYY-MM-DD
        if "/" in date_raw:
            parts = date_raw.split("/")
            if len(parts) == 3:
                date_str = f"{parts[2]}-{int(parts[1]):02d}-{int(parts[0]):02d}"
            else:
                date_str = date_raw
        else:
            date_str = date_raw.split("T")[0]

        if len(numbers) >= 6:
            formatted_data.append({
                "date": date_str,
                "result": sorted(numbers[:6])
            })
    return formatted_data

# Alias tương thích bot.py
fetch_and_update_vietlott_655 = fetch_vietlott_655_data

def get_dataset(game="655"):
    target_file = DATA_FILE_645 if str(game) == "645" else DATA_FILE_655
    fetch_func = fetch_vietlott_645_data if str(game) == "645" else fetch_vietlott_655_data
    
    if os.path.exists(target_file):
        try:
            with open(target_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data and len(data) > 0:
                    return data
        except Exception:
            pass
    return fetch_func()