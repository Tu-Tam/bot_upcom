import requests
import json
import os
import csv
import re

DATA_FILE_655 = "vietlott_655.json"
DATA_FILE_645 = "vietlott_645.json"

GITHUB_655_URLS = [
    "https://raw.githubusercontent.com/vietvudanh/vietlott-data/main/data/power655.jsonl",
    "https://raw.githubusercontent.com/vietvudanh/vietlott-data/main/data/power655.csv"
]

# Thêm endpoint chuẩn xác cho Mega 6/45
GITHUB_645_URLS = [
    "https://raw.githubusercontent.com/vietvudanh/vietlott-data/main/data/power645.jsonl",
    "https://raw.githubusercontent.com/vietvudanh/vietlott-data/main/data/mega645.csv",
    "https://raw.githubusercontent.com/hieund12/Data-Vietlott/master/result645.csv"
]

def fetch_vietlott_655_data(limit=300):
    return _fetch_multi_source(GITHUB_655_URLS, DATA_FILE_655, limit)

def fetch_vietlott_645_data(limit=300):
    res = _fetch_multi_source(GITHUB_645_URLS, DATA_FILE_645, limit)
    # Nếu CDN lỗi, tự động cào từ API dự phòng
    if not res or len(res) == 0:
        res = _fetch_fallback_api("645", DATA_FILE_645, limit)
    return res

def _fetch_multi_source(urls, filename, limit):
    results = []

    for url in urls:
        try:
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                text_data = res.text.strip()
                lines = text_data.splitlines()
                
                if url.endswith(".csv") or (lines and "," in lines[0] and "date" in lines[0].lower()):
                    reader = csv.reader(lines)
                    header = next(reader, None)
                    for row in reader:
                        parsed = _extract_csv_row(row, header)
                        if parsed:
                            results.append(parsed)
                elif "\n" in text_data and not text_data.startswith("["):
                    for line in lines:
                        if line.strip():
                            try:
                                item = json.loads(line)
                                parsed = _extract_json_item(item)
                                if parsed:
                                    results.append(parsed)
                            except Exception:
                                continue
                else:
                    data_list = json.loads(text_data)
                    if isinstance(data_list, list):
                        for item in data_list:
                            parsed = _extract_json_item(item)
                            if parsed:
                                results.append(parsed)

                if results:
                    break
        except Exception as e:
            print(f"Lỗi fetch {url}: {e}")

    if not results and os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                results = json.load(f)
        except Exception:
            pass

    return _process_and_save(results, filename, limit)

def _fetch_fallback_api(game_type, filename, limit):
    """API dự phòng khi GitHub CDN bị lỗi URL"""
    results = []
    try:
        api_url = f"https://api.vietlott.vn/api/v1/result/{game_type}"
        res = requests.get(api_url, timeout=10)
        if res.status_code == 200:
            data = res.json()
            items = data.get("data", []) if isinstance(data, dict) else data
            for item in items:
                parsed = _extract_json_item(item)
                if parsed:
                    results.append(parsed)
    except Exception as e:
        print(f"Lỗi API dự phòng {game_type}: {e}")
        
    return _process_and_save(results, filename, limit)

def _process_and_save(results, filename, limit):
    if results:
        unique_map = {}
        for item in results:
            if item and isinstance(item, dict) and "date" in item and len(item["date"]) == 10:
                unique_map[item['date']] = item
            
        results = sorted(list(unique_map.values()), key=lambda x: x["date"])
        
        if limit and len(results) > limit:
            results = results[-limit:]

        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    return results

def _clean_date_string(date_raw):
    if not date_raw:
        return None
    raw_str = str(date_raw).replace('{"date":', '').replace('"', '').replace('{', '').replace('}', '').strip()
    match = re.search(r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})', raw_str)
    if match:
        return f"{match.group(1)}-{int(match.group(2)):02d}-{int(match.group(3)):02d}"
    
    match_rev = re.search(r'(\d{1,2})[-/](\d{1,2})[-/](\d{4})', raw_str)
    if match_rev:
        return f"{match_rev.group(3)}-{int(match_rev.group(2)):02d}-{int(match_rev.group(1)):02d}"
    return None

def _extract_json_item(item):
    if not isinstance(item, dict):
        return None

    date_raw = item.get("date") or item.get("draw_date") or item.get("run_date") or item.get("drawDate") or item.get("periodDate") or ""
    nums_raw = item.get("result") or item.get("numbers") or item.get("draw_result") or item.get("winning_numbers") or []

    date_clean = _clean_date_string(date_raw)
    if not date_clean or not nums_raw:
        return None

    nums = []
    if isinstance(nums_raw, str):
        nums = [int(x) for x in re.findall(r'\d+', nums_raw)]
    elif isinstance(nums_raw, list):
        nums = [int(x) for x in nums_raw if str(x).isdigit()]

    if len(nums) >= 6:
        return {"date": date_clean, "result": sorted(nums[:6])}
    return None

def _extract_csv_row(row, header):
    if not row or len(row) < 2:
        return None
    try:
        date_clean = _clean_date_string(row[0])
        nums = []
        for cell in row[1:]:
            nums.extend([int(x) for x in re.findall(r'\d+', str(cell))])
        
        if date_clean and len(nums) >= 6:
            return {"date": date_clean, "result": sorted(nums[:6])}
    except Exception:
        pass
    return None

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