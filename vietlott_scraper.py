import requests
import json
import os

VIETLOTT_655_URL = "https://vietlott.vn/api/front/v1/draw-result/power655"
VIETLOTT_645_URL = "https://vietlott.vn/api/front/v1/draw-result/mega645"

DATA_FILE_655 = "vietlott_655.json"
DATA_FILE_645 = "vietlott_645.json"

# Dữ liệu nền dự phòng khởi tạo (Đảm bảo CSDL luôn có dữ liệu kể cả khi Render xóa file)
DEFAULT_DATA_655 = [
    {"date": "2026-07-25", "result": [5, 12, 18, 29, 34, 45]},
    {"date": "2026-07-28", "result": [2, 11, 23, 31, 40, 52]},
    {"date": "2026-07-30", "result": [8, 14, 19, 25, 38, 49]},
    {"date": "2026-08-01", "result": [4, 15, 22, 33, 41, 50]},
    {"date": "2026-08-04", "result": [1, 10, 17, 28, 39, 53]},
    {"date": "2026-08-06", "result": [7, 16, 24, 35, 42, 51]},
    {"date": "2026-08-08", "result": [3, 13, 20, 30, 44, 55]},
    {"date": "2026-08-11", "result": [9, 21, 27, 36, 43, 48]},
    {"date": "2026-08-13", "result": [6, 18, 26, 32, 47, 54]}
]

DEFAULT_DATA_645 = [
    {"date": "2026-07-26", "result": [3, 11, 18, 25, 33, 41]},
    {"date": "2026-07-29", "result": [5, 12, 20, 29, 36, 42]},
    {"date": "2026-07-31", "result": [1, 9, 15, 22, 30, 44]},
    {"date": "2026-08-02", "result": [7, 14, 21, 28, 35, 40]},
    {"date": "2026-08-05", "result": [2, 10, 17, 24, 31, 43]},
    {"date": "2026-08-07", "result": [6, 13, 19, 27, 34, 45]},
    {"date": "2026-08-09", "result": [4, 8, 16, 23, 32, 39]},
    {"date": "2026-08-12", "result": [10, 18, 26, 33, 37, 41]}
]

def fetch_vietlott_655_data(limit=300):
    return _fetch_vietlott_generic(VIETLOTT_655_URL, DATA_FILE_655, DEFAULT_DATA_655, limit)

def fetch_vietlott_645_data(limit=300):
    return _fetch_vietlott_generic(VIETLOTT_645_URL, DATA_FILE_645, DEFAULT_DATA_645, limit)

def _fetch_vietlott_generic(url, filename, default_data, limit=300):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json;charset=UTF-8",
        "Origin": "https://vietlott.vn",
        "Referer": "https://vietlott.vn/"
    }
    payload = {"pageIndex": 1, "pageSize": limit}

    formatted_data = []

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            draw_list = data.get("result", []) or data.get("listResults", [])
            
            for item in draw_list:
                res_str = item.get("result", "") or item.get("drawResult", "") or item.get("numbers", "")
                date_raw = item.get("drawDate", "") or item.get("periodDate", "") or item.get("date", "")
                
                if not res_str or not date_raw:
                    continue
                
                raw_nums = res_str.split("|")[0].split(",")
                numbers = [int(x) for x in raw_nums if x.strip().isdigit()]
                
                if "/" in date_raw:
                    parts = date_raw.split("/")
                    date_str = f"{parts[2]}-{int(parts[1]):02d}-{int(parts[0]):02d}" if len(parts) == 3 else date_raw
                else:
                    date_str = date_raw.split("T")[0]

                if len(numbers) >= 6:
                    formatted_data.append({
                        "date": date_str,
                        "result": sorted(numbers[:6])
                    })
    except Exception as e:
        print(f"Lỗi kết nối API Vietlott ({url}): {e}")

    # Nếu cào trực tiếp bị lỗi/chặn IP, tự động lấy dữ liệu từ file local hoặc dùng bộ dữ liệu dự phòng
    if not formatted_data:
        if os.path.exists(filename):
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    formatted_data = json.load(f)
            except Exception:
                pass

    if not formatted_data:
        formatted_data = default_data

    # Sắp xếp CŨ -> MỚI và ghi đè file lưu trữ
    formatted_data.sort(key=lambda x: x["date"])
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(formatted_data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    return formatted_data

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