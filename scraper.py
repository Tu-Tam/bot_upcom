import re
import requests

from bs4 import BeautifulSoup
from datetime import datetime

from database import save_result


URL = "https://xsmb.com.vn/so-ket-qua-xsmb-100-ngay"


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/120 Safari/537.36"
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
    soup = BeautifulSoup(html, "html.parser")

    text = soup.get_text("\n")

    results = []

    # Tìm ngày dạng dd/mm/yyyy
    date_pattern = re.compile(
        r"(?:XSMB|SXMB).*?"
        r"(\d{1,2})/(\d{1,2})/(\d{4})"
        r".*?"
        r"ĐB\s*\|\s*(\d{5})",
        re.S
    )

    for match in date_pattern.finditer(text):

        day = int(match.group(1))
        month = int(match.group(2))
        year = int(match.group(3))

        special = match.group(4)

        try:
            dt = datetime(
                year,
                month,
                day
            )

            results.append({
                "date": dt.strftime("%Y-%m-%d"),
                "special": special
            })

        except ValueError:
            continue

    return results


def update_database():
    html = fetch_page()

    results = parse_results(html)

    count = 0

    for item in results:

        save_result(
            item["date"],
            item["special"]
        )

        count += 1

    return count


if __name__ == "__main__":

    count = update_database()

    print(
        f"Đã cập nhật {count} kết quả."
    )
