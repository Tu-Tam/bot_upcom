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

    soup = BeautifulSoup(html, "html.parser")

    # Lấy toàn bộ text của trang
    text = soup.get_text("\n")

    # Chuẩn hóa khoảng trắng
    text = re.sub(r"\r", "", text)

    results = []

    # Tìm từng cụm:
    #
    # XSMB ... dd/mm/yyyy
    # ...
    # ĐB | 12345
    #
    pattern = re.compile(
        r"XSMB.*?"
        r"(\d{1,2})/(\d{1,2})/(\d{4})"
        r".{0,1500}?"
        r"ĐB\s*\|\s*(\d{5})",
        re.S | re.I
    )

    for match in pattern.finditer(text):

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

    # Sắp xếp theo ngày
    results.sort(
        key=lambda x: x["date"]
    )

    return results


def update_database():

    print("Đang tải dữ liệu XSMB...")

    html = fetch_page()

    print(
        f"Đã tải trang: {len(html):,} ký tự"
    )

    results = parse_results(html)

    print(
        f"Đã tìm thấy {len(results)} kết quả"
    )

    count = 0

    for item in results:

        try:

            save_result(
                item["date"],
                item["special"]
            )

            count += 1

            print(
                f"Đã lưu: "
                f"{item['date']} - "
                f"{item['special']}"
            )

        except Exception as e:

            print(
                f"Lỗi lưu {item['date']}: {e}"
            )

    return count


if __name__ == "__main__":

    count = update_database()

    print(
        f"Đã cập nhật {count} kết quả."
    )
