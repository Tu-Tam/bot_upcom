import requests
import json
import os

VIETLOTT_655_URL = "https://vietlott.vn/api/front/v1/draw-result/power655"
DATA_FILE = "vietlott_655.json"

def fetch_vietlott_655_data(limit=200):
    """
    Hàm cào dữ liệu chính được gọi từ bot.py
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Content-Type": "application/json"
    }
    payload = {
        "pageIndex": 1,
        "pageSize": limit
    }

    try:
        response = requests.post(VIETLOTT_655_URL, json=payload, headers=headers, timeout=15)
        if response.status_code == 200:
            data = response.json()
            draw_list = data.get("result", [])
            
            formatted_data = []
            for item in draw_list:
                res_str = item.get("result", "")
                date_raw = item.get("drawDate", "")
                
                if not res_str or not date_raw:
                    continue
                
                numbers = [int(x) for x in res_str.split("|")[0].split(",") if x.strip().isdigit()]
                
                if "/" in date_raw:
                    parts = date_raw.split("/")
                    date_str = f"{parts[2]}-{parts[1]:0>2}-{parts[0]:0>2}" if len(parts) == 3 else date_raw
                else:
                    date_str = date_raw

                if len(numbers) >= 6:
                    formatted_data.append({
                        "date": date_str,
                        "result": sorted(numbers[:6])
                    })

            formatted_data.sort(key=lambda x: x["date"])

            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(formatted_data, f, ensure_ascii=False, indent=2)
                
            return formatted_data
    except Exception as e:
        print(f"Lỗi cào dữ liệu: {e}")
        
    return []

# Bổ sung alias để gọi tên nào cũng chạy được
fetch_and_update_vietlott_655 = fetch_vietlott_655_data

def get_dataset():
    """Hàm lấy dataset từ json"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return fetch_vietlott_655_data()