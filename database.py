import sqlite3
import threading

db_lock = threading.Lock()

def init_db():
    """Khởi tạo bảng lưu trữ kết quả xổ số"""
    with db_lock:
        conn = sqlite3.connect('xosomb.db')
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS results (
                date TEXT PRIMARY KEY,
                numbers TEXT
            )
        ''')
        conn.commit()
        conn.close()

def save_result(date_str, numbers):
    """Lưu hoặc cập nhật kết quả 1 ngày (Nhận 2 tham số: date_str và numbers)"""
    with db_lock:
        try:
            conn = sqlite3.connect('xosomb.db')
            cursor = conn.cursor()
            
            numbers_str = ",".join(numbers) if isinstance(numbers, list) else str(numbers)
            
            cursor.execute('''
                INSERT OR REPLACE INTO results (date, numbers)
                VALUES (?, ?)
            ''', (date_str, numbers_str))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"⚠️ Lỗi CSDL khi lưu ngày {date_str}: {e}", flush=True)
            return False

def get_results(limit=90):
    """Lấy danh sách kết quả xổ số gần nhất từ CSDL"""
    with db_lock:
        try:
            conn = sqlite3.connect('xosomb.db')
            cursor = conn.cursor()
            cursor.execute('SELECT date, numbers FROM results ORDER BY date DESC LIMIT ?', (limit,))
            rows = cursor.fetchall()
            conn.close()
            
            # Chuyển đổi chuỗi numbers lại thành danh sách các số
            results = []
            for date, numbers_str in rows:
                num_list = numbers_str.split(',') if numbers_str else []
                results.append({'date': date, 'numbers': num_list})
            return results
        except Exception as e:
            print(f"⚠️ Lỗi lấy dữ liệu CSDL: {e}", flush=True)
            return []

def count_results():
    """Đếm tổng số ngày đã lưu trong CSDL"""
    with db_lock:
        try:
            conn = sqlite3.connect('xosomb.db')
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM results')
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except Exception as e:
            print(f"⚠️ Lỗi đếm CSDL: {e}", flush=True)
            return 0

# Tự động khởi tạo DB khi module được load
init_db()