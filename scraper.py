import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime

from database import save_result


URL = "https://xsmb.com.vn/so-ket-qua-xsmb-100-ngay"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def fetch_page():
    response = requests.get(
        URL,
        headers=HEADERS,
        timeout=30
    )

    response.raise_for_status()

    return response.text


def parse_results(html):

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    text = soup.get_text("\n")

    # Chuẩn hóa khoảng trắng
    text = re.sub(
        r"[ \t]+",
        " ",
        text
    )

    results = []

    # Tìm từng cụm:
    #
    # XSMB Thứ ..., dd/mm/yyyy
    # ...
    # ĐB | 12345
    #
    pattern = re.compile(
        r"XSMB.*?"
        r"(\d{1,2}/\d{1,2}/\d{4})"
        r".*?"
        r"ĐB\s*\|\s*(\d{5})",
        re.S
    )

    matches = pattern.finditer(text)

    for match in matches:

        date_text = match.group(1)
        special = match.group(2)

        try:

            dt = datetime.strptime(
                date_text,
                "%d/%m/%Y"
            )

        except ValueError:

            continue

        results.append({
            "date": dt.strftime("%Y-%m-%d"),
            "special": special
        })

    # Loại bỏ ngày trùng
    unique = {}

    for item in results:
        unique[item["date"]] = item["special"]

    results = [
        {
            "date": date,
            "special": special
        }
        for date, special in unique.items()
    ]

    # Mới nhất trước
    results.sort(
        key=lambda x: x["date"],
        reverse=True
    )

    return results


def update_database():

    html = fetch_page()

    results = parse_results(html)

    print(
        f"Scraper tìm thấy {len(results)} kết quả."
    )

    count = 0

    for item in results:

        save_result(
            item["date"],
            item["special"]
        )

        count += 1

    print(
        f"Đã lưu {count} kết quả vào database."
    )

    return count


if __name__ == "__main__":

    count = update_database()

    print(
        f"Đã cập nhật {count} kết quả."
    )
