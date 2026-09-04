# vietlott_scraper.py
import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime

DATA_FILE = "vietlott_history.json"

def update_historical_data(limit=300):
    url = "https://vietlott.vn/vi/trung-thuong/ket-qua-trung-thuong/655"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    results = []
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            rows = soup.select('table.table-hover tbody tr')
            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 2:
                    date_str = datetime.strptime(cols[0].text.strip(), "%d/%m/%Y").strftime("%Y-%m-%d")
                    nums = [int(n.text.strip()) for n in cols[1].find_all('span', class_='ball')[:6]]
                    results.append({"date": date_str, "game": "655", "result": sorted(nums)})
            
            # Lưu file cache
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            return len(results)
    except Exception as e:
        print(f"Lỗi scraping: {e}")
    return 0

def load_dataset():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []