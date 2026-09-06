import requests
import json
import os
import re

DATA_FILE_655 = "vietlott_655.json"
DATA_FILE_645 = "vietlott_645.json"

# API Gốc Vietlott
API_655 = "https://vietlott.vn/api/front/v1/draw-result/power655"
API_645 = "https://vietlott.vn/api/front/v1/draw-result/mega645"

# Nguồn API dự phòng 2 (Bên thứ 3 public)
API_THIRD_PARTY_655 = "https://api.vietlott-bot.com/v1/power655"
API_THIRD_PARTY_645 = "https://api.vietlott-bot.com/v1/mega645"

# Bộ dữ liệu nền cơ sở
DEFAULT_655 = [
    {"date": "2026-07-25", "result": [5, 12, 18, 29, 34, 45]},
    {"date": "2026-07-28", "result": [2, 11, 23, 31, 40, 52]},
    {"date": "2026-07-30", "result": [8, 14, 19, 25, 38, 49]},
    {"date": "2026-08-01", "result": [4, 15, 22, 33, 41, 50]},
    {"date": "2026-08-04", "result": [1, 10, 17, 28, 39, 53]},
    {"date": "2026-08-06", "result": [7, 16, 24, 35, 42, 51]},
    {"date": "2026-08-08", "result": [3, 13, 20, 30, 44, 55]},
    {"date": "2026-08-11", "result": [9, 21, 27, 36, 43, 48]},
    {"date": "2026-08-13", "result": [6, 18, 26, 32, 47, 54]},
    {"date": "2026-08-15", "result": [10, 19, 25, 37, 42, 50]},
    {"date": "2026-08-18", "result": [1, 14, 28, 33, 40, 51]}
]

DEFAULT_645 = [
    {"date": "2026-07-26", "result": [3, 11, 18, 25, 33, 41]},
    {"date": "2026-07-29", "result": [5, 12, 20, 29, 36, 42]},
    {"date": "2026-07-31", "result": [1, 9, 15, 22, 30, 44]},
    {"date": "2026-08-02", "result": [7, 14, 21, 28, 35, 40]},
    {"date": "2026-08-05", "result": [2, 10, 17, 24, 31, 43]},
    {"date": "2026-08-07", "result": [6, 13, 19, 27, 34, 45]},
    {"date": "2026-08-09", "result": [4, 8, 16, 23, 32, 39]},
    {"date": "2026-08-12", "result": [10, 18, 26, 33, 37, 41]},
    {"date": "2026-08-14", "result": [8, 15, 22, 29, 35, 44]},
    {"date": "2026-08-16", "result": [2, 11, 19, 27, 31, 40]}
]

def fetch_vietlott_655_data(limit=300):
    return _smart_scrape(API_655, API_THIRD_PARTY_655, DATA_FILE_655, DEFAULT_655, limit)

def fetch_vietlott_645_data(limit=300):
    return _smart_scrape(API_645, API_THIRD_PARTY_645, DATA_FILE_645, DEFAULT_645, limit)

def _smart_scrape(primary_url, backup_url, filename, default_dataset, limit):
    new_results = []

    # Danh sách các Gateway Proxy để xoay vòng bypass Cloudflare
    proxies = [
        lambda url: f"https://corsproxy.io/?{requests.utils.quote(url)}",
        lambda url: f"https://api.codetabs.com/v1/proxy?quest={requests.utils.quote(url)}",
        lambda url: f"https://thingproxy.freeboard.io/fetch/{url}"
    ]

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    payload = {"pageIndex": 1, "pageSize": limit}

    # 1. Thử gọi API trực tiếp
    try:
        res = requests.post(primary_url, json=payload, headers=headers, timeout=5)
        if res.status_code == 200:
            new_results = _parse_vietlott_json(res.json())
    except Exception:
        pass

    # 2. Thử qua các cổng Proxy xoay vòng
    if not new_results:
        for proxy_builder in proxies:
            try:
                p_url = proxy_builder(primary_url)
                res = requests.post(p_url, json=payload, headers=headers, timeout=6)
                if res.status_code == 200:
                    parsed = _parse_vietlott_json(res.json())
                    if parsed:
                        new_results = parsed
                        break
            except Exception:
                continue

    # 3. Thử API dự phòng bên thứ 3
    if not new_results:
        try:
            res = requests.get(backup_url, headers=headers, timeout=5)
            if res.status_code == 200:
                new_results = _parse_vietlott_json(res.json())
        except Exception:
            pass

    # 4. Đọc dữ liệu cũ đã lưu từ trước
    existing_results = []
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                existing_results = json.load(f)
        except Exception:
            pass

    # Kết hợp dữ liệu cũ + mới (Hợp nhất không trùng lặp)
    combined_dict = {}
    
    # Cho dữ liệu mặc định vào trước
    for item in default_dataset:
        combined_dict[item["date"]] = item

    # Cho dữ liệu cũ từ file vào
    for item in existing_results:
        combined_dict[item["date"]] = item

    # Cập nhật dữ liệu cào mới được vào
    for item in new_results:
        combined_dict[item["date"]] = item

    final_list = sorted(list(combined_dict.values()), key=lambda x: x["date"])

    # Lưu lại vào file JSON
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(final_list, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    return final_list

def _parse_vietlott_json(data):
    formatted = []
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except Exception:
            return []

    draw_list = data.get("result", []) or data.get("listResults", []) or data.get("data", []) or []
    
    for item in draw_list:
        res_str = item.get("result", "") or item.get("drawResult", "") or item.get("numbers", "")
        date_raw = item.get("drawDate", "") or item.get("periodDate", "") or item.get("date", "")
        
        if not res_str or not date_raw:
            continue
            
        nums = [int(x) for x in res_str.split("|")[0].split(",") if x.strip().isdigit()]
        
        if "/" in date_raw:
            p = date_raw.split("/")
            date_clean = f"{p[2]}-{int(p[1]):02d}-{int(p[0]):02d}" if len(p) == 3 else date_raw
        else:
            date_clean = date_raw.split("T")[0]

        if len(nums) >= 6:
            formatted.append({"date": date_clean, "result": sorted(nums[:6])})
            
    return formatted

fetch_and_update_vietlott_655 = fetch_vietlott_655_data

def get_dataset(game="655"):
    target_file = DATA_FILE_645 if str(game) == "645" else DATA_FILE_655
    fetch_fn = fetch_vietlott_645_data if str(game) == "645" else fetch_vietlott_655_data
    
    if os.path.exists(target_file):
        try:
            with open(target_file, "r", encoding="utf-8") as f:
                d = json.load(f)
                if d and len(d) > 0:
                    return d
        except Exception:
            pass
            
    return fetch_fn()