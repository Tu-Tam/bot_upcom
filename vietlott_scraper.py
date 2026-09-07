import requests
import json
import os
import csv

DATA_FILE_655 = "vietlott_655.json"
DATA_FILE_645 = "vietlott_645.json"

GITHUB_655_URLS = [
    "https://raw.githubusercontent.com/vietvudanh/vietlott-data/main/data/power655.jsonl",
    "https://raw.githubusercontent.com/vietvudanh/vietlott-data/main/data/power655.csv"
]

GITHUB_645_URLS = [
    "https://raw.githubusercontent.com/vietvudanh/vietlott-data/main/data/mega.jsonl",
    "https://raw.githubusercontent.com/vietvudanh/vietlott-data/main/data/mega645.jsonl",
    "https://raw.githubusercontent.com/vietvudanh/vietlott-data/main/data/mega645.csv"
]

def fetch_vietlott_655_data(limit=300):
    return _fetch_multi_source(GITHUB_655_URLS, DATA_FILE_655, limit)

def fetch_vietlott_645_data(limit=300):
    return _fetch_multi_source(GITHUB_645_URLS, DATA_FILE_645, limit)

def _fetch_multi_source(urls, filename, limit):
    results = []

    for url in urls:
        try:
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                text_data = res.text.strip()
                
                if url.endswith(".csv") or ("," in text_data.split('\n')[0] and "date" in text_data.split('\n')[0].lower()):
                    lines = text_data.splitlines()
                    reader = csv.reader(lines)
                    header = next(reader, None)
                    for row in reader:
                        parsed = _extract_csv_row(row, header)
                        if parsed:
                            results.append(parsed)
                elif "\n" in text_data and not text_data.startswith("["):
                    for line in text_data.split('\n'):
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

    if results:
        unique_map = {}
        for item in results:
            if item and "date" in item and len(item["date"]) == 10:
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

def _extract_json_item(item):
    if not isinstance(item, dict):
        return None

    date_raw = item.get("date") or item.get("draw_date") or item.get("run_date") or item.get("drawDate") or ""
    nums_raw = item.get("result") or item.get("numbers") or item.get("draw_result") or item.get("winning_numbers") or []

    if not date_raw or not nums_raw:
        return None

    # Chuẩn hóa sạch Date string
    date_str = str(date_raw).replace('{"date":"', '').replace('"', '').split("T")[0].replace("/", "-").strip()
    parts = date_str.split("-")
    
    if len(parts) == 3:
        if len(parts[0]) == 4:
            date_clean = f"{parts[0]}-{int(parts[1]):02d}-{int(parts[2]):02d}"
        else:
            date_clean = f"{parts[2]}-{int(parts[1]):02d}-{int(parts[0]):02d}"
    else:
        return None

    nums = []
    if isinstance(nums_raw, str):
        nums = [int(x) for x in nums_raw.replace("|", ",").split(",") if x.strip().isdigit()]
    elif isinstance(nums_raw, list):
        nums = [int(x) for x in nums_raw if str(x).isdigit()]

    if len(nums) >= 6:
        return {"date": date_clean, "result": sorted(nums[:6])}
    return None

def _extract_csv_row(row, header):
    if not row or len(row) < 2:
        return None
    try:
        date_raw = row[0].strip().replace('"', '')
        nums = []
        for cell in row[1:]:
            cell_clean = cell.strip()
            if cell_clean.isdigit():
                nums.append(int(cell_clean))
            elif "-" in cell_clean or "," in cell_clean or "|" in cell_clean:
                nums.extend([int(x) for x in cell_clean.replace("|", ",").replace("-", ",").split(",") if x.strip().isdigit()])
        
        if date_raw and len(nums) >= 6:
            parts = date_raw.split("T")[0].replace("/", "-").split("-")
            if len(parts) == 3:
                if len(parts[0]) == 4:
                    date_clean = f"{parts[0]}-{int(parts[1]):02d}-{int(parts[2]):02d}"
                else:
                    date_clean = f"{parts[2]}-{int(parts[1]):02d}-{int(parts[0]):02d}"
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