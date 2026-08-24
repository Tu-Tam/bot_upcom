import re
import time
import requests

from bs4 import BeautifulSoup
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from database import save_result


PRIMARY_URL = "https://xoso.com.vn/xsmb-100-ngay.html"
FALLBACK_URLS = [
    "https://xoso.com.vn/xsmb-30-ngay.html",
    "https://xsmb.com.vn/xsmb-sxmb-ket-qua-xo-so-mien-bac-truc-tiep",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7"
}

TIMEOUT = 30
RETRY_MAX = 3


def create_session():
    session = requests.Session()
    adapter = HTTPAdapter(max_retries=Retry(
        total=RETRY_MAX, backoff_factor=1.5,
        status_forcelist=[429,500,502,503,504]
    ))
    session.mount("https://", adapter)
    session.headers.update(HEADERS)
    return session


def fetch_page(url):
    print(f"\n🔗 Đọc nguồn: {url}")
    s = create_session()
    resp = s.get(url, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.text


def normalize_text(t):
    return re.sub(r"\s+", " ", t.replace("\xa0"," ")).strip()


def parse_html(html):
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for tbl in soup.find_all("table"):
        text = tbl.get_text("\n")
        m_date = re.search(r"(\d{1,2}/\d{1,2}/\d{4})", text)
        if not m_date: continue
        try:
            dt = datetime.strptime(m_date.group(), "%d/%m/%Y")
            day_id = dt.strftime("%Y-%m-%d")
        except Exception: continue

        rec = {
            "date": day_id, "weekday": dt.weekday(), "special": None,
            "g1": [], "g2": [], "g3": [], "g4": [], "g5": [], "g6": [], "g7": [],
            "loto_by_head": {}
        }
        for tr in tbl.find_all("tr"):
            cells = [normalize_text(td.get_text()) for td in tr.find_all(["td","th"])]
            if len(cells)<2: continue
            tieu = cells[0].upper().strip(":.")
            so = re.findall(r"\b\d{2,5}\b", " ".join(cells[1:]))
            if tieu in ("ĐB","ĐẶC BIỆT") and len(so)>=1 and len(so[0])==5:
                rec["special"]=so[0]
            elif tieu=="1": rec["g1"]+=so
            elif tieu=="2": rec["g2"]+=so
            elif tieu=="3": rec["g3"]+=so
            elif tieu=="4": rec["g4"]+=so
            elif tieu=="5": rec["g5"]+=so
            elif tieu=="6": rec["g6"]+=so
            elif tieu=="7": rec["g7"]+=so
        if rec["special"]:
            out.append(rec)
            print(f"✅ Phân tích: {day_id} | ĐB={rec['special']}")
    return out


def fetch_and_parse_all():
    for url in [PRIMARY_URL]+FALLBACK_URLS:
        try:
            html = fetch_page(url)
            data = parse_html(html)
            if data: return data
        except Exception as e:
            print(f"⚠️ Nguồn {url}: {e}")
    return []


if __name__=="__main__":
    from database import init_db
    init_db()
    print("🚀 Quét dữ liệu...")
    ds = fetch_and_parse_all()
    for rec in ds: save_result(rec)
    print(f"✅ Hoàn tất: {len(ds)} ngày đã lưu.")
