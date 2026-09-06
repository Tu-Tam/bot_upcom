import requests
import json
import os

VIETLOTT_655_URL = "https://vietlott.vn/api/front/v1/draw-result/power655"
VIETLOTT_645_URL = "https://vietlott.vn/api/front/v1/draw-result/mega645"

DATA_FILE_655 = "vietlott_655.json"
DATA_FILE_645 = "vietlott_645.json"

def fetch_vietlott_655_data(limit=300):
    """Cào dữ liệu Power 6/55"""
    return _fetch_vietlott_generic(VIETLOTT_655_URL, DATA_FILE_655, limit)

def fetch_vietlott_645_data(limit=300):
    """Cào dữ liệu Mega 6/45"""
    return _fetch_vietlott_generic(VIETLOTT_645_URL, DATA_FILE_645, limit)

def _fetch_vietlott_generic(url, filename, limit=300):
    # Header chuẩn trình duyệt thực tế chống chặn 403/405
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json;charset=UTF-8",
        "Origin": "https://vietlott.vn",
        "Referer": "https://vietlott.vn/"
    }
    
    payload = {
        "pageIndex": 1,
        "pageSize": limit
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        if response.status_code == 200:
            data = response.json()
            
            # Xử lý đa dạng cấu trúc JSON trả về của Vietlott
            draw_list = data.get("result", [])
            if not draw_list and isinstance(data.get("listResults"), list):
                draw_list = data.get("listResults")
            
            formatted_data = []
            for item in draw_list:
                # Tìm chuỗi kết quả
                res_str = item.get("result", "") or item.get("drawResult", "") or item.get("numbers", "")
                # Tìm ngày quay
                date_raw = item.get("drawDate", "") or item.get("periodDate", "") or item.get("date", "")
                
                if not res_str or not date_raw:
                    continue
                
                # Bóc tách các số
                raw_nums = res_str.split("|")[0].split(",")
                numbers = [int(x) for x in raw_nums if x.strip().isdigit()]
                
                # Chuẩn hóa ngày về YYYY-MM-DD
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

            # Sắp xếp CŨ -> MỚI
            formatted_data.sort(key=lambda x: x["date"])

            if formatted_data:
                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(formatted_data, f, ensure_ascii=False, indent=2)
                
            return formatted_data
        else:
            print(f"Lỗi HTTP {response.status_code} từ Vietlott API")
    except Exception as e:
        print(f"Lỗi cào dữ liệu Vietlott ({url}): {e}")
        
    return []

# Giữ alias cho bot.py
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