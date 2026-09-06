import requests
import json
import os
import re
from bs4 import BeautifulSoup

DATA_FILE_655 = "vietlott_655.json"
DATA_FILE_645 = "vietlott_645.json"

# API Vietlott chính thức
URL_655 = "https://vietlott.vn/api/front/v1/draw-result/power655"
URL_645 = "https://vietlott.vn/api/front/v1/draw-result/mega645"

# Nguồn web HTML dự phòng (dành cho cào dữ liệu thực tế khi API chặn Cloud IP)
WEB_655 = "https://vietlott.vn/vi/trung-thuong/ket-qua-truc-tiep/power-655"
WEB_645 = "https://vietlott.vn/vi/trung-thuong/ket-qua-truc-tiep/mega-645"

def fetch_vietlott_655_data(limit=300):
    return _fetch_vietlott_all(URL_655, WEB_655, DATA_FILE_655, limit)

def fetch_vietlott_645_data(limit=300):
    return _fetch_vietlott_all(URL_645, WEB_645, DATA_FILE_645, limit)

def _fetch_vietlott_all(api_url, web_url, filename, limit):
    results = []

    # Cách 1: Thử cào qua API JSON chính thức
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Content-Type": "application/json",
        "Origin": "https://vietlott.vn",
        "Referer": "https://vietlott.vn/"
    }
    
    try:
        res = requests.post(api_url, json={"pageIndex": 1, "pageSize": limit}, headers=headers, timeout=10)
        if res.status_code == 200:
            data = res.json()
            draw_list = data.get("result", []) or data.get("listResults", [])
            for item in draw_list:
                res_str = item.get("result", "") or item.get("drawResult", "")
                date_raw = item.get("drawDate", "") or item.get("periodDate", "")
                if res_str and date_raw:
                    nums = [int(x) for x in res_str.split("|")[0].split(",") if x.strip().isdigit()]
                    date_clean = date_raw.split("T")[0].replace("/", "-")
                    if "/" in date_raw:
                        p = date_raw.split("/")
                        if len(p) == 3:
                            date_clean = f"{p[2]}-{int(p[1]):02d}-{int(p[0]):02d}"
                    if len(nums) >= 6:
                        results.append({"date": date_clean, "result": sorted(nums[:6])})
    except Exception:
        pass

    # Cách 2: Nếu API bị chặn, cào trực tiếp HTML giao diện Vietlott
    if not results:
        try:
            web_res = requests.get(web_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            if web_res.status_code == 200:
                soup = BeautifulSoup(web_res.text, 'html.parser')
                # Bóc tách các dòng kết quả từ table HTML của Vietlott
                rows = soup.find_all('tr')
                for row in rows:
                    date_elem = row.find(text=re.compile(r'\d{2}/\d{2}/\d{4}'))
                    nums_elems = row.find_all('span', class_=re.compile(r'ball|day_so'))
                    if date_elem and len(nums_elems) >= 6:
                        parts = date_elem.strip().split('/')
                        date_clean = f"{parts[2]}-{parts[1]}-{parts[0]}"
                        nums = [int(e.text.strip()) for e in nums_elems if e.text.strip().isdigit()]
                        if len(nums) >= 6:
                            results.append({"date": date_clean, "result": sorted(nums[:6])})
        except Exception:
            pass

    # Cách 3: Lấy từ file CSDL đã lưu trước đó nếu có
    if not results and os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                results = json.load(f)
        except Exception:
            pass

    # Lọc bỏ trùng lặp và sắp xếp theo ngày (CŨ -> MỚI)
    if results:
        unique_results = {item['date']: item for item in results}.values()
        results = sorted(list(unique_results), key=lambda x: x["date"])
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    return results

def get_dataset(game="655"):
    target_file = DATA_FILE_645 if str(game) == "645" else DATA_FILE_655
    fetch_fn = fetch_vietlott_645_data if str(game) == "645" else fetch_vietlott_655_data
    
    if os.path.exists(target_file):
        try:
            with open(target_file, "r", encoding="utf-8") as f:
                d = json.load(f)
                if d: 
                    return d
        except Exception:
            pass
    return fetch_fn()