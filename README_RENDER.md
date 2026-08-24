# Hướng dẫn triển khai trên Render

- Sử dụng 1 instance duy nhất hoặc đặt WEB_CONCURRENCY=1 để tránh nhiều tiến trình ghi đồng thời khi vẫn dùng SQLite.
- Nếu cần scale, chuyển DATABASE_PATH sang một Postgres do Render cung cấp (managed DB).
- Start command: `web: python bot.py`
